"""Position analysis prompts for bilingual portfolio analysis."""

SYSTEM_PROMPT_ZH = """你是一位专业的投资组合分析师。基于用户的持仓数据，提供深入的分析和优化建议。

分析要求：
1. 持仓结构分析：行业分布、集中度、风险暴露
2. 单个持仓评估：标记价格异常、涨跌原因、估值合理性
3. 优化建议：减仓/加仓建议、再平衡方案、风险管理
4. 宏观视角：当前市场环境对持仓的影响

输出要求：
- 使用 Markdown 格式
- 包含具体数据和数字
- 建议要具体可执行
- 风险提示要明确
- 不要编造数据，只基于提供的数据分析"""

SYSTEM_PROMPT_EN = """You are a professional portfolio analyst. Provide in-depth analysis and optimization suggestions based on the user's holdings data.

Analysis requirements:
1. Portfolio structure: sector distribution, concentration, risk exposure
2. Individual position evaluation: price anomalies, movement drivers, valuation reasonableness
3. Optimization suggestions: reduce/add suggestions, rebalancing plan, risk management
4. Macro perspective: current market environment impact on holdings

Output requirements:
- Use Markdown format
- Include specific data and numbers
- Suggestions must be actionable
- Risk warnings must be clear
- Do not fabricate data, only analyze based on provided data"""


def build_user_prompt_zh(account_data: dict, positions: list[dict]) -> str:
    """Build Chinese user prompt with position data."""
    lines = [
        "## 账户概览",
        f"- 总权益: {account_data.get('total_equity', 0):,.2f}",
        f"- 现金: {account_data.get('cash', 0):,.2f}",
        f"- 持仓市值: {account_data.get('stock_value', 0):,.2f}",
        f"- 报告日期: {account_data.get('report_date', 'N/A')}",
        "",
        "## 持仓明细",
        "| 标的 | 数量 | 市价 | 市值 | 日涨跌% | 未实现盈亏 | 仓位% |",
        "|------|------|------|------|---------|-----------|-------|",
    ]
    for p in positions:
        lines.append(
            f"| {p.get('symbol', '')} | {p.get('quantity', 0):.0f} | "
            f"{p.get('mark_price', 0):.2f} | {p.get('position_value', 0):,.2f} | "
            f"{p.get('previous_day_change_percent', 0) or 0:.2f}% | "
            f"{p.get('total_unrealized_pnl', 0):,.2f} | "
            f"{p.get('percent_of_nav', 0):.2f}% |"
        )
    lines.append("")
    lines.append("请基于以上数据，用中文提供详细的持仓分析和优化建议。")
    return "\n".join(lines)


def build_user_prompt_en(account_data: dict, positions: list[dict]) -> str:
    """Build English user prompt with position data."""
    lines = [
        "## Account Overview",
        f"- Total Equity: {account_data.get('total_equity', 0):,.2f}",
        f"- Cash: {account_data.get('cash', 0):,.2f}",
        f"- Stock Value: {account_data.get('stock_value', 0):,.2f}",
        f"- Report Date: {account_data.get('report_date', 'N/A')}",
        "",
        "## Position Details",
        "| Symbol | Qty | Price | Value | Day Chg% | Unrealized PnL | Weight% |",
        "|--------|-----|-------|-------|----------|----------------|---------|",
    ]
    for p in positions:
        lines.append(
            f"| {p.get('symbol', '')} | {p.get('quantity', 0):.0f} | "
            f"{p.get('mark_price', 0):.2f} | {p.get('position_value', 0):,.2f} | "
            f"{p.get('previous_day_change_percent', 0) or 0:.2f}% | "
            f"{p.get('total_unrealized_pnl', 0):,.2f} | "
            f"{p.get('percent_of_nav', 0):.2f}% |"
        )
    lines.append("")
    lines.append("Based on the above data, provide a detailed portfolio analysis and optimization suggestions in English.")
    return "\n".join(lines)
