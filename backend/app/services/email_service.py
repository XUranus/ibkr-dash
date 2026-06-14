"""Email service — SMTP send for test emails and daily review notifications."""

from __future__ import annotations

import html
import json
import logging
import os
import re
import smtplib
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TEST_SUBJECT = "IBKR DASH 邮件发送测试"
DEFAULT_TEST_MESSAGE = "如果你收到这封邮件，说明 IBKR DASH 邮件配置成功。"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MASKED_PASSWORD_MARKER = "****"


class EmailConfigError(ValueError):
    """Raised when email configuration is invalid."""


class EmailSendError(RuntimeError):
    """Raised when SMTP delivery fails."""


@dataclass
class EmailConfig:
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_ssl: bool = True
    smtp_use_starttls: bool = False
    email_from: str = ""
    email_to: str = ""
    enabled: bool = False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_smtp_password(password: str | None) -> str:
    if not password:
        return ""
    value = password.strip()
    if len(value) <= 8:
        return MASKED_PASSWORD_MARKER
    return f"{MASKED_PASSWORD_MARKER}{value[-4:]}"


def is_masked_password(value: str | None) -> bool:
    return bool(value and MASKED_PASSWORD_MARKER in value)


def parse_email_recipients(value: str) -> list[str]:
    recipients = [item.strip() for item in value.split(",") if item.strip()]
    invalid = [item for item in recipients if not EMAIL_RE.match(item)]
    if invalid:
        raise EmailConfigError(f"邮箱地址格式不正确：{', '.join(invalid)}")
    return recipients


def _format_money(value: Any) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return "--"


def _format_percent(value: Any) -> str:
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "--"


def _format_plain(value: Any) -> str:
    if value is None or value == "":
        return "--"
    return str(value)


class EmailConfigStore:
    def __init__(self, config_file: str) -> None:
        self.config_file = Path(config_file).expanduser()

    def exists(self) -> bool:
        return self.config_file.exists()

    def read(self) -> EmailConfig:
        if not self.config_file.exists():
            return EmailConfig()
        try:
            with self.config_file.open("r", encoding="utf-8") as f:
                payload = json.load(f)
        except json.JSONDecodeError as exc:
            raise EmailConfigError("邮件配置文件不是合法 JSON") from exc
        if not isinstance(payload, dict):
            raise EmailConfigError("邮件配置文件必须是 JSON object")
        return EmailConfig(
            smtp_host=str(payload.get("smtp_host") or ""),
            smtp_port=int(payload.get("smtp_port") or 465),
            smtp_username=str(payload.get("smtp_username") or ""),
            smtp_password=str(payload.get("smtp_password") or ""),
            smtp_use_ssl=bool(payload.get("smtp_use_ssl", True)),
            smtp_use_starttls=bool(payload.get("smtp_use_starttls", False)),
            email_from=str(payload.get("email_from") or ""),
            email_to=str(payload.get("email_to") or ""),
            enabled=bool(payload.get("enabled", False)),
        )

    def save(self, config: EmailConfig) -> None:
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with self.config_file.open("w", encoding="utf-8") as f:
            json.dump(asdict(config), f, ensure_ascii=False, indent=2)
            f.write("\n")


class EmailService:
    def __init__(self, config_file: str, store: EmailConfigStore | None = None) -> None:
        self.store = store or EmailConfigStore(config_file)

    def get_config(self) -> EmailConfig:
        return self._effective_config()

    def update_config(self, payload: dict[str, Any]) -> EmailConfig:
        current = self._effective_config()
        password = current.smtp_password
        if payload.get("smtp_password") and not is_masked_password(payload["smtp_password"]):
            password = payload["smtp_password"].strip()

        config = EmailConfig(
            smtp_host=str(payload.get("smtp_host") or "").strip(),
            smtp_port=int(payload.get("smtp_port") or 465),
            smtp_username=str(payload.get("smtp_username") or "").strip(),
            smtp_password=password,
            smtp_use_ssl=bool(payload.get("smtp_use_ssl", True)),
            smtp_use_starttls=bool(payload.get("smtp_use_starttls", False)),
            email_from=str(payload.get("email_from") or "").strip(),
            email_to=str(payload.get("email_to") or "").strip(),
            enabled=bool(payload.get("enabled", False)),
        )
        self._validate(config, require_all=config.enabled)
        self.store.save(config)
        return config

    def test_send(self, subject: str | None = None, message: str | None = None) -> dict:
        config = self._effective_config()
        self._validate(config, require_all=True)
        body = (message or DEFAULT_TEST_MESSAGE).strip() or DEFAULT_TEST_MESSAGE
        title = (subject or DEFAULT_TEST_SUBJECT).strip() or DEFAULT_TEST_SUBJECT
        recipients = parse_email_recipients(config.email_to)
        html_body = f"<p>{html.escape(body)}</p>"
        self._send(config, subject=title, html_body=html_body, text_body=body, recipients=recipients)
        return {"success": True, "message": "测试邮件已发送", "sent_to": recipients, "sent_at": utc_now_iso()}

    def send_daily_review(self, review_document: dict[str, Any]) -> bool:
        config = self._effective_config()
        if not config.enabled:
            return False
        recipients = parse_email_recipients(config.email_to)
        report_date = str(review_document.get("report_date") or "")
        summary = review_document.get("summary") or "无总结"
        subject = f"【IBKR每日持仓复盘】{report_date}"
        html_body = self._build_review_html(review_document, report_date, summary)
        text_body = self._build_review_text(review_document, report_date, summary)
        self._send(config, subject=subject, html_body=html_body, text_body=text_body, recipients=recipients)
        return True

    def _build_review_html(self, doc: dict, report_date: str, summary: str) -> str:
        overview = doc.get("deterministic_context", {}).get("overview", {})
        sections = [
            "<h2>今日账户概览</h2>",
            "<ul>",
            f"<li><strong>日期：</strong>{html.escape(report_date)}</li>",
            f"<li><strong>总权益：</strong>{html.escape(_format_money(overview.get('total_equity')))}</li>",
            f"<li><strong>当日盈亏：</strong>{html.escape(_format_money(overview.get('daily_pnl')))}</li>",
            "</ul>",
            f"<h2>一句话总结</h2><p>{html.escape(summary)}</p>",
            f"<h2>涨跌归因</h2><p>{html.escape(_format_plain(doc.get('attribution_summary')))}</p>",
            f"<h2>账户结论</h2><p>{html.escape(_format_plain(doc.get('account_conclusion')))}</p>",
            f"<h2>风险分析</h2><p>{html.escape(_format_plain(doc.get('risk_analysis')))}</p>",
        ]
        return (
            "<!doctype html><html><head><meta charset=\"utf-8\"></head>"
            '<body style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;line-height:1.6;color:#172033;">'
            + "\n".join(sections) + "</body></html>"
        )

    def _build_review_text(self, doc: dict, report_date: str, summary: str) -> str:
        overview = doc.get("deterministic_context", {}).get("overview", {})
        return "\n".join([
            f"IBKR 每日持仓复盘 - {report_date}",
            "=" * 40,
            f"总权益：{_format_money(overview.get('total_equity'))}",
            f"当日盈亏：{_format_money(overview.get('daily_pnl'))}",
            f"一句话总结：{summary}",
            f"涨跌归因：{_format_plain(doc.get('attribution_summary'))}",
            f"账户结论：{_format_plain(doc.get('account_conclusion'))}",
            f"风险分析：{_format_plain(doc.get('risk_analysis'))}",
        ])

    def _send(self, config: EmailConfig, *, subject: str, html_body: str, text_body: str, recipients: list[str]) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = config.email_from
        message["To"] = ", ".join(recipients)
        message.set_content(text_body, subtype="plain", charset="utf-8")
        message.add_alternative(html_body, subtype="html", charset="utf-8")
        try:
            if config.smtp_use_ssl:
                with smtplib.SMTP_SSL(config.smtp_host, config.smtp_port, timeout=20) as smtp:
                    smtp.login(config.smtp_username, config.smtp_password)
                    smtp.send_message(message)
                return
            with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=20) as smtp:
                if config.smtp_use_starttls:
                    smtp.starttls()
                smtp.login(config.smtp_username, config.smtp_password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailSendError(f"邮件发送失败：{exc}") from exc

    def _effective_config(self) -> EmailConfig:
        if self.store.exists():
            return self.store.read()
        return EmailConfig(
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "465") or "465"),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_use_ssl=os.getenv("SMTP_USE_SSL", "true").lower() in ("1", "true", "yes"),
            smtp_use_starttls=os.getenv("SMTP_USE_STARTTLS", "false").lower() in ("1", "true", "yes"),
            email_from=os.getenv("EMAIL_FROM", ""),
            email_to=os.getenv("EMAIL_TO", ""),
            enabled=os.getenv("EMAIL_ENABLED", "false").lower() in ("1", "true", "yes"),
        )

    def _validate(self, config: EmailConfig, *, require_all: bool) -> None:
        if config.smtp_use_ssl and config.smtp_use_starttls:
            raise EmailConfigError("SMTP SSL 和 STARTTLS 不能同时开启")
        if config.smtp_port < 1 or config.smtp_port > 65535:
            raise EmailConfigError("SMTP 端口必须在 1-65535 之间")
        if require_all:
            missing = []
            for field_name, label in (("smtp_host", "SMTP Host"), ("smtp_username", "SMTP Username"), ("smtp_password", "SMTP Password"), ("email_from", "Email From")):
                if not str(getattr(config, field_name) or "").strip():
                    missing.append(label)
            if missing:
                raise EmailConfigError(f"启用邮件发送时必须填写：{', '.join(missing)}")
        if config.enabled and not config.email_to.strip():
            raise EmailConfigError("启用邮件发送时必须填写收件人 (email_to)")


__all__ = ["EmailService", "EmailConfig", "EmailConfigStore", "EmailConfigError", "EmailSendError"]
