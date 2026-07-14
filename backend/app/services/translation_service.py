"""Translation service for bilingual agent output.

Generates Chinese translations of English agent output text fields,
storing both versions in the document.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Trade review text fields that need translation
TRADE_REVIEW_TEXT_FIELDS = [
    "summary",
]

TRADE_REVIEW_LIST_FIELDS = [
    "strengths",
    "weaknesses",
    "improvement_suggestions",
    "data_limitations",
    "evidence_used",
]

# Daily review text fields that need translation
DAILY_REVIEW_TEXT_FIELDS = [
    "summary",
    "account_conclusion",
    "attribution_summary",
    "market_context",
    "risk_analysis",
    "operation_observation",
]

DAILY_REVIEW_LIST_FIELDS = [
    "data_limitations",
    "evidence_used",
]

# Nested list-of-dict fields with text content
DAILY_REVIEW_NESTED_TEXT_FIELDS = {
    "major_contributors_analysis": ["analysis"],
    "major_drags_analysis": ["analysis"],
    "focus_symbol_analyses": [
        "price_action",
        "account_impact",
        "valuation_note",
        "cost_position_note",
    ],
    "tomorrow_watchlist": ["reason"],
}

TRADE_REVIEW_NESTED_TEXT_FIELDS: dict[str, list[str]] = {}


def _build_translation_prompt(
    text_map: dict[str, str],
    source_lang: str = "English",
    target_lang: str = "Chinese",
) -> str:
    """Build a translation prompt for a batch of texts."""
    return (
        f"Translate the following texts from {source_lang} to {target_lang}. "
        f"Keep financial terms, stock symbols, numbers, and percentages unchanged. "
        f"Return a JSON object mapping each key to its translation. "
        f"Only output the JSON object, no markdown, no explanation.\n\n"
        f"Texts to translate:\n{json.dumps(text_map, ensure_ascii=False)}"
    )


def _call_llm_for_translation(
    llm_service: LLMService,
    text_map: dict[str, str],
    source_lang: str = "English",
    target_lang: str = "Chinese",
) -> dict[str, str]:
    """Call LLM to translate a batch of texts."""
    if not text_map:
        return {}

    prompt = _build_translation_prompt(text_map, source_lang, target_lang)
    try:
        raw = llm_service.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are a professional financial translator. "
                        "Translate accurately while keeping financial terminology natural. "
                        "Only output valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(raw, strict=False)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items() if k in text_map}
    except Exception as exc:
        logger.warning("Translation LLM call failed: %s", exc)
    return {}


def _collect_texts(
    payload: dict,
    text_fields: list[str],
    list_fields: list[str],
    nested_fields: dict[str, list[str]],
) -> dict[str, str]:
    """Collect all translatable text fields into a flat map."""
    text_map: dict[str, str] = {}

    for field in text_fields:
        val = payload.get(field)
        if isinstance(val, str) and val.strip():
            text_map[field] = val

    for field in list_fields:
        val = payload.get(field)
        if isinstance(val, list):
            for i, item in enumerate(val):
                if isinstance(item, str) and item.strip():
                    text_map[f"{field}[{i}]"] = item

    for parent_field, child_fields in nested_fields.items():
        parent_val = payload.get(parent_field)
        if isinstance(parent_val, list):
            for i, item in enumerate(parent_val):
                if isinstance(item, dict):
                    for cf in child_fields:
                        cv = item.get(cf)
                        if isinstance(cv, str) and cv.strip():
                            text_map[f"{parent_field}[{i}].{cf}"] = cv
                        elif isinstance(cv, list):
                            for j, sub in enumerate(cv):
                                if isinstance(sub, str) and sub.strip():
                                    text_map[f"{parent_field}[{i}].{cf}[{j}]"] = sub

    return text_map


def _apply_translations(
    payload: dict,
    translations: dict[str, str],
    text_fields: list[str],
    list_fields: list[str],
    nested_fields: dict[str, list[str]],
) -> dict:
    """Apply translations back to the payload."""
    result = dict(payload)

    for field in text_fields:
        key = field
        if key in translations:
            result[field] = translations[key]

    for field in list_fields:
        key_prefix = f"{field}["
        translated = []
        val = result.get(field)
        if isinstance(val, list):
            for i, item in enumerate(val):
                key = f"{field}[{i}]"
                if key in translations:
                    translated.append(translations[key])
                else:
                    translated.append(item)
            result[field] = translated

    for parent_field, child_fields in nested_fields.items():
        parent_val = result.get(parent_field)
        if isinstance(parent_val, list):
            translated_parent = []
            for i, item in enumerate(parent_val):
                if isinstance(item, dict):
                    new_item = dict(item)
                    for cf in child_fields:
                        key = f"{parent_field}[{i}].{cf}"
                        if key in translations:
                            new_item[cf] = translations[key]
                        elif isinstance(new_item.get(cf), list):
                            translated_sub = []
                            for j, sub in enumerate(new_item[cf]):
                                sub_key = f"{parent_field}[{i}].{cf}[{j}]"
                                if sub_key in translations:
                                    translated_sub.append(translations[sub_key])
                                else:
                                    translated_sub.append(sub)
                            new_item[cf] = translated_sub
                    translated_parent.append(new_item)
                else:
                    translated_parent.append(item)
            result[parent_field] = translated_parent

    return result


def translate_trade_review_output(
    llm_service: LLMService,
    payload: dict,
    source_lang: str = "English",
    target_lang: str = "Chinese",
) -> dict:
    """Translate trade review output text fields."""
    text_map = _collect_texts(
        payload,
        TRADE_REVIEW_TEXT_FIELDS,
        TRADE_REVIEW_LIST_FIELDS,
        TRADE_REVIEW_NESTED_TEXT_FIELDS,
    )
    if not text_map:
        return payload

    translations = _call_llm_for_translation(llm_service, text_map, source_lang, target_lang)
    if not translations:
        return payload

    return _apply_translations(
        payload, translations,
        TRADE_REVIEW_TEXT_FIELDS,
        TRADE_REVIEW_LIST_FIELDS,
        TRADE_REVIEW_NESTED_TEXT_FIELDS,
    )


def translate_daily_review_output(
    llm_service: LLMService,
    payload: dict,
    source_lang: str = "English",
    target_lang: str = "Chinese",
) -> dict:
    """Translate daily review output text fields."""
    text_map = _collect_texts(
        payload,
        DAILY_REVIEW_TEXT_FIELDS,
        DAILY_REVIEW_LIST_FIELDS,
        DAILY_REVIEW_NESTED_TEXT_FIELDS,
    )
    if not text_map:
        return payload

    translations = _call_llm_for_translation(llm_service, text_map, source_lang, target_lang)
    if not translations:
        return payload

    return _apply_translations(
        payload, translations,
        DAILY_REVIEW_TEXT_FIELDS,
        DAILY_REVIEW_LIST_FIELDS,
        DAILY_REVIEW_NESTED_TEXT_FIELDS,
    )
