"""Position analysis prompts for bilingual portfolio analysis."""

SYSTEM_PROMPT_ZH = """你是一位专业的投资组合分析师。基于持仓数据，给出简洁的分析结论和优化建议。

要求：
- 200字以内，信息密度高
- 重点：结论、风险点、改进建议
- 不要列举持仓明细（数据已提供）
- 用 Markdown 格式，包含具体数字
- 不要编造数据"""

SYSTEM_PROMPT_EN = """You are a professional portfolio analyst. Based on holdings data, provide concise analysis conclusions and optimization suggestions.

Requirements:
- Under 200 words, high information density
- Focus: conclusions, risks, improvement suggestions
- Do not list position details (data is provided)
- Use Markdown format with specific numbers
- Do not fabricate data"""


def _build_data_section(account_data: dict, positions: list[dict], lang: str) -> str:
    """Build the data section (same for both languages)."""
    lines = [
        f"Total Equity: {account_data.get('total_equity', 0):,.2f}",
        f"Cash: {account_data.get('cash', 0):,.2f}",
        f"Report Date: {account_data.get('report_date', 'N/A')}",
        "",
        "Positions (sorted by value):",
    ]
    for p in positions:
        chg = p.get('previous_day_change_percent', 0) or 0
        upnl = p.get('total_unrealized_pnl', 0)
        lines.append(
            f"- {p.get('symbol', '')}: qty={p.get('quantity', 0):.0f} "
            f"value={p.get('position_value', 0):,.0f} "
            f"chg={chg:+.2f}% upnl={upnl:+,.0f} "
            f"weight={p.get('percent_of_nav', 0):.1f}%"
        )
    return "\n".join(lines)


def build_user_prompt_zh(account_data: dict, positions: list[dict]) -> str:
    """Build Chinese user prompt."""
    data = _build_data_section(account_data, positions, "zh")
    return f"{data}\n\n请用中文给出简洁的分析结论和优化建议（200字以内）。重点分析：集中度风险、行业暴露、需要关注的持仓、改进建议。"


def build_user_prompt_en(account_data: dict, positions: list[dict]) -> str:
    """Build English user prompt."""
    data = _build_data_section(account_data, positions, "en")
    return f"{data}\n\nProvide concise analysis conclusions and optimization suggestions (under 200 words). Focus on: concentration risk, sector exposure, positions to watch, improvement suggestions."
