"""Position Analysis agent.

Generates bilingual (Chinese + English) portfolio analysis reports
using LLM. Results are stored in the database for frontend display.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.agents.position_analysis.prompts import (
    SYSTEM_PROMPT_EN,
    SYSTEM_PROMPT_ZH,
    build_user_prompt_en,
    build_user_prompt_zh,
)

logger = logging.getLogger(__name__)


async def generate_position_analysis(
    db: Any,
    llm_service: Any,
    report_date: str,
) -> dict | None:
    """Generate a bilingual position analysis report.

    1. Load account + position data from DB
    2. Build prompts for ZH and EN
    3. Call LLM for each language
    4. Save both reports to DB

    Returns:
        Saved document dict, or None if LLM unavailable.
    """
    if not llm_service or not getattr(llm_service, 'api_key', None):
        logger.info("LLM not configured, skipping position analysis")
        return None

    logger.info("Starting position analysis for %s", report_date)

    # Step 1: Load data
    account = db.execute_one(
        "SELECT * FROM account_snapshots ORDER BY report_date DESC LIMIT 1"
    )
    if not account:
        logger.warning("No account data found, skipping analysis")
        return None

    effective_date = report_date or account.get("report_date", "")
    positions = db.execute(
        """
        SELECT symbol, description, asset_class, quantity, mark_price,
               position_value, percent_of_nav, previous_day_change_percent,
               total_unrealized_pnl, total_realized_pnl, average_cost_price,
               cost_basis_money
        FROM position_snapshots
        WHERE report_date = ?
        ORDER BY position_value DESC
        """,
        (effective_date,),
    )

    if not positions:
        logger.warning("No positions found for %s", effective_date)
        return None

    account_data = {
        "total_equity": float(account.get("total_equity") or 0),
        "cash": float(account.get("cash") or 0),
        "stock_value": float(account.get("stock_value") or 0),
        "report_date": effective_date,
    }

    # Step 2: Generate Chinese report
    prompt_zh = build_user_prompt_zh(account_data, positions)
    messages_zh = [
        {"role": "system", "content": SYSTEM_PROMPT_ZH},
        {"role": "user", "content": prompt_zh},
    ]
    try:
        report_zh = llm_service.chat(messages_zh, timeout=120)
    except Exception as exc:
        logger.warning("Failed to generate Chinese report: %s", exc)
        report_zh = ""

    # Step 3: Generate English report
    prompt_en = build_user_prompt_en(account_data, positions)
    messages_en = [
        {"role": "system", "content": SYSTEM_PROMPT_EN},
        {"role": "user", "content": prompt_en},
    ]
    try:
        report_en = llm_service.chat(messages_en, timeout=120)
    except Exception as exc:
        logger.warning("Failed to generate English report: %s", exc)
        report_en = ""

    if not report_zh and not report_en:
        logger.warning("Both reports empty, skipping save")
        return None

    # Step 4: Save to DB
    analysis_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    db.upsert("position_analysis", {
        "id": analysis_id,
        "report_date": effective_date,
        "analysis_zh": report_zh,
        "analysis_en": report_en,
        "created_at": now,
    }, conflict_cols=["id"])

    logger.info("Saved position analysis %s for %s", analysis_id, effective_date)
    return {
        "id": analysis_id,
        "report_date": effective_date,
        "analysis_zh": report_zh,
        "analysis_en": report_en,
        "created_at": now,
    }
