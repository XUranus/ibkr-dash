"""Position analysis prompts for 7-dimension structured scoring."""

SYSTEM_PROMPT_ZH = """你是持仓管理分析 Agent。基于持仓数据和 Longbridge 公开数据，输出结构化的7维度评分分析。

评分维度（总分100）：
1. company_quality（公司质量，满分20）：基于 description 和 Longbridge 数据判断公司基本面质量
2. valuation_quality（估值质量，满分15）：基于 PE、PB、机构目标价判断估值水平
3. trend_strength（趋势强度，满分15）：基于价格趋势、技术指标判断趋势强度
4. account_fit（账户适配，满分20）：基于 percent_of_nav、现金比例、集中度判断仓位适配
5. risk_reward（风险收益，满分15）：基于 unrealized_pnl、上行/下行空间判断风险收益比
6. review_constraints（复盘约束，满分10）：基于历史复盘数据判断约束条件
7. event_catalyst（事件催化，满分5）：基于财报日、机构评级、新闻判断催化强度

输出要求：
- 必须输出严格 JSON object，不要 Markdown。
- score_detail 包含全部 7 个维度 key，每个包含 score、max_score、reason。
- overall_score = 所有维度 score 之和。
- 如果数据不足，在 data_limitations 中说明，不要编造。
- 不要列举持仓明细（数据已提供）。
- 每个维度的 reason 必须包含具体数字和分析，不能只写"数据不足"。

JSON schema:
{
  "overall_score": 0-100,
  "rating": "excellent|good|fair|poor",
  "summary": "2-3句总结，包含关键数据",
  "score_detail": {
    "company_quality": {"score": 0-20, "max_score": 20, "reason": "包含公司基本面分析"},
    "valuation_quality": {"score": 0-15, "max_score": 15, "reason": "包含PE、目标价等估值数据"},
    "trend_strength": {"score": 0-15, "max_score": 15, "reason": "包含价格趋势和技术指标"},
    "account_fit": {"score": 0-20, "max_score": 20, "reason": "包含仓位分布和流动性分析"},
    "risk_reward": {"score": 0-15, "max_score": 15, "reason": "包含上行/下行空间分析"},
    "review_constraints": {"score": 0-10, "max_score": 10, "reason": "包含复盘约束分析"},
    "event_catalyst": {"score": 0-5, "max_score": 5, "reason": "包含事件催化分析"}
  },
  "position_advice": {
    "action": "add|hold|reduce|close",
    "target_pct": 0,
    "max_pct": 0,
    "rationale": "仓位调整理由",
    "urgency": "high|medium|low"
  },
  "strengths": ["优点1", "优点2"],
  "weaknesses": ["风险1", "风险2"],
  "key_risks": ["关键风险1"],
  "catalyst_events": ["近期催化事件"],
  "valuation_context": {
    "pe_ratio": "PE值及行业对比",
    "analyst_consensus": "分析师共识",
    "target_price": "目标价"
  },
  "technical_levels": {
    "support": ["支撑位"],
    "resistance": ["阻力位"],
    "trend": "上升|下降|震荡"
  },
  "data_limitations": []
}"""

SYSTEM_PROMPT_EN = """You are a position management analysis Agent. Output structured 7-dimension scoring based on holdings data.

Scoring dimensions (total 100):
1. company_quality (max 20): Fundamental quality based on company description
2. valuation_quality (max 15): Valuation level based on asset class and description
3. trend_strength (max 15): Price trend based on daily change and cumulative performance
4. account_fit (max 20): Position sizing based on weight, cash ratio, concentration
5. risk_reward (max 15): Risk/reward based on unrealized PnL and position value
6. review_constraints (max 10): Review constraints from historical data
7. event_catalyst (max 5): Event catalyst strength

Output requirements:
- Strict JSON object only, no Markdown.
- score_detail must include all 7 dimension keys, each with score, max_score, reason.
- overall_score = sum of all dimension scores.
- Write data_limitations if data is insufficient. Do not fabricate.
- Do not list position details (data is provided).

JSON schema: same as Chinese version."""


def _build_data_section(account_data: dict, positions: list[dict], lang: str, enrichment: dict | None = None) -> str:
    """Build the data section (same for both languages)."""
    total_equity = account_data.get('total_equity', 0)
    cash = account_data.get('cash', 0)
    lines = [
        f"Total Equity: ${total_equity:,.2f}",
        f"Cash: ${cash:,.2f}",
        f"Cash Ratio: {cash/total_equity*100:.1f}%" if total_equity > 0 else "Cash Ratio: N/A",
        f"Position Count: {len(positions)}",
        f"Report Date: {account_data.get('report_date', 'N/A')}",
        "",
        "Positions (sorted by value):",
    ]
    for p in positions:
        chg = p.get('previous_day_change_percent', 0) or 0
        upnl = p.get('total_unrealized_pnl', 0)
        weight = p.get('percent_of_nav', 0) or 0
        lines.append(
            f"- {p.get('symbol', '')} ({p.get('description', '')}): "
            f"qty={p.get('quantity', 0):.0f} "
            f"value=${p.get('position_value', 0):,.0f} "
            f"weight={weight:.1f}% "
            f"chg={chg:+.2f}% "
            f"unrealized_pnl={upnl:+,.0f}"
        )

    # Add enrichment data from Longbridge
    if enrichment:
        lines.append("")
        lines.append("Longbridge Public Data:")
        for p in positions:
            sym = p.get('symbol', '')
            if sym in enrichment:
                edata = enrichment[sym]
                parts = []
                # Valuation
                val = edata.get('valuation', {})
                if val:
                    pe = val.get('pe_ttm') or val.get('pe')
                    pb = val.get('pb')
                    if pe:
                        parts.append(f"PE(TTM)={pe}")
                    if pb:
                        parts.append(f"PB={pb}")
                # Forecast
                fc = edata.get('forecast', {})
                if fc:
                    target = fc.get('target_price') or fc.get('consensus_target')
                    if target:
                        parts.append(f"TargetPrice={target}")
                # Quote
                qt = edata.get('quote', {})
                if qt:
                    mkt_cap = qt.get('market_cap')
                    if mkt_cap:
                        parts.append(f"MarketCap={mkt_cap}")
                if parts:
                    lines.append(f"- {sym}: {', '.join(parts)}")

    return "\n".join(lines)


def build_user_prompt_zh(account_data: dict, positions: list[dict], enrichment: dict | None = None) -> str:
    """Build Chinese user prompt with 7-dimension scoring."""
    data = _build_data_section(account_data, positions, "zh", enrichment)
    return f"{data}\n\n请基于以上数据输出结构化的7维度评分分析，并提供仓位建议、执行计划、优缺点分析（JSON格式）。"


def build_user_prompt_en(account_data: dict, positions: list[dict], enrichment: dict | None = None) -> str:
    """Build English user prompt with 7-dimension scoring."""
    data = _build_data_section(account_data, positions, "en", enrichment)
    return f"{data}\n\nOutput structured 7-dimension scoring analysis with position advice, execution plan, strengths/weaknesses (JSON format)."
