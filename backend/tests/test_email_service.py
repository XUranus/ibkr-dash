"""Tests for EmailService."""

import json
import tempfile
from pathlib import Path

from app.services.email_service import (
    EmailConfig,
    EmailConfigError,
    EmailConfigStore,
    EmailService,
    parse_email_recipients,
    mask_smtp_password,
    is_masked_password,
)


class TestParseRecipients:
    def test_single(self):
        assert parse_email_recipients("a@b.com") == ["a@b.com"]

    def test_multiple(self):
        result = parse_email_recipients("a@b.com, c@d.com")
        assert result == ["a@b.com", "c@d.com"]

    def test_invalid_raises(self):
        try:
            parse_email_recipients("not-an-email")
            assert False, "Should have raised"
        except EmailConfigError:
            pass


class TestPasswordMasking:
    def test_mask_short(self):
        assert mask_smtp_password("abc") == "****"

    def test_mask_long(self):
        result = mask_smtp_password("abcdefghijklmnop")
        assert result.startswith("****")
        assert result.endswith("mnop")

    def test_mask_none(self):
        assert mask_smtp_password(None) == ""

    def test_is_masked(self):
        assert is_masked_password("****") is True
        assert is_masked_password("real_password") is False
        assert is_masked_password(None) is False


class TestEmailConfigStore:
    def test_save_and_read(self, tmp_path):
        config_file = tmp_path / "email.json"
        store = EmailConfigStore(str(config_file))
        config = EmailConfig(smtp_host="smtp.test.com", smtp_port=587, enabled=True)
        store.save(config)
        assert store.exists()
        loaded = store.read()
        assert loaded.smtp_host == "smtp.test.com"
        assert loaded.smtp_port == 587
        assert loaded.enabled is True

    def test_read_nonexistent(self, tmp_path):
        config_file = tmp_path / "nonexistent.json"
        store = EmailConfigStore(str(config_file))
        config = store.read()
        assert config.smtp_host == ""
        assert config.enabled is False


class TestEmailService:
    def test_get_config_from_env(self, tmp_path):
        config_file = str(tmp_path / "email.json")
        service = EmailService(config_file)
        config = service.get_config()
        assert isinstance(config, EmailConfig)

    def test_update_config(self, tmp_path):
        config_file = str(tmp_path / "email.json")
        service = EmailService(config_file)
        config = service.update_config({
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_username": "user@test.com",
            "smtp_password": "secret123",
            "email_from": "from@test.com",
            "email_to": "to@test.com",
            "enabled": True,
        })
        assert config.smtp_host == "smtp.test.com"
        assert config.smtp_password == "secret123"
        assert config.enabled is True

    def test_update_config_masked_password_preserved(self, tmp_path):
        config_file = str(tmp_path / "email.json")
        service = EmailService(config_file)
        service.update_config({
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_username": "user",
            "smtp_password": "original_password",
            "email_from": "from@test.com",
            "email_to": "to@test.com",
            "enabled": True,
        })
        # Update with masked password — should preserve original
        config = service.update_config({
            "smtp_host": "smtp.test.com",
            "smtp_port": 587,
            "smtp_username": "user",
            "smtp_password": "****",
            "email_from": "from@test.com",
            "email_to": "to@test.com",
            "enabled": True,
        })
        assert config.smtp_password == "original_password"

    def test_validate_ssl_and_starttls(self, tmp_path):
        config_file = str(tmp_path / "email.json")
        service = EmailService(config_file)
        try:
            service.update_config({
                "smtp_host": "smtp.test.com",
                "smtp_port": 465,
                "smtp_username": "user",
                "smtp_password": "pass",
                "email_from": "from@test.com",
                "email_to": "to@test.com",
                "smtp_use_ssl": True,
                "smtp_use_starttls": True,
                "enabled": False,
            })
            assert False, "Should have raised"
        except EmailConfigError as e:
            assert "不能同时开启" in str(e)
