"""Scoring dimension definitions for position analysis and trade review.

Single source of truth for max scores, dimension keys, and display labels.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Position Analysis (持仓分析) — 7 dimensions, total 100
# ---------------------------------------------------------------------------

POSITION_ANALYSIS_DIMENSIONS: dict[str, dict] = {
    "company_quality": {
        "key": "company_quality",
        "label_zh": "公司质量",
        "label_en": "Company Quality",
        "max_score": 20,
        "description": "基本面质量：盈利能力、收入增长、利润率、现金流",
    },
    "valuation_quality": {
        "key": "valuation_quality",
        "label_zh": "估值质量",
        "label_en": "Valuation Quality",
        "max_score": 15,
        "description": "估值水平：PE、PS、EV/Sales、同业比较",
    },
    "trend_strength": {
        "key": "trend_strength",
        "label_zh": "趋势强度",
        "label_en": "Trend Strength",
        "max_score": 15,
        "description": "价格趋势：近期涨幅、相对基准表现、技术信号",
    },
    "account_fit": {
        "key": "account_fit",
        "label_zh": "账户适配",
        "label_en": "Account Fit",
        "max_score": 20,
        "description": "仓位适配：当前仓位比例、流动性、集中度",
    },
    "risk_reward": {
        "key": "risk_reward",
        "label_zh": "风险收益",
        "label_en": "Risk/Reward",
        "max_score": 15,
        "description": "风险收益比：上行潜力、下行风险、风险收益比",
    },
    "review_constraints": {
        "key": "review_constraints",
        "label_zh": "复盘约束",
        "label_en": "Review Constraints",
        "max_score": 10,
        "description": "复盘约束：历史错误标签、复盘警告",
    },
    "event_catalyst": {
        "key": "event_catalyst",
        "label_zh": "事件催化",
        "label_en": "Event Catalyst",
        "max_score": 5,
        "description": "事件催化：财报窗口、新闻情绪、机构评级变化",
    },
}

POSITION_ANALYSIS_TOTAL_MAX = 100

# ---------------------------------------------------------------------------
# Trade Review (交易复盘) — 8 dimensions, total 100
# ---------------------------------------------------------------------------

TRADE_REVIEW_DIMENSIONS: dict[str, dict] = {
    "profit_result": {
        "key": "profit_result",
        "label_zh": "收益结果",
        "label_en": "Profit Result",
        "max_score": 20,
        "description": "已实现和未实现盈亏、收益率",
    },
    "relative_return": {
        "key": "relative_return",
        "label_zh": "相对收益",
        "label_en": "Relative Return",
        "max_score": 15,
        "description": "相对 QQQ/SPY/SMH 的表现",
    },
    "entry_quality": {
        "key": "entry_quality",
        "label_zh": "买点质量",
        "label_en": "Entry Quality",
        "max_score": 15,
        "description": "买入时机、价格位置、基本面支撑",
    },
    "exit_quality": {
        "key": "exit_quality",
        "label_zh": "卖点质量",
        "label_en": "Exit Quality",
        "max_score": 15,
        "description": "卖出时机、是否卖飞、止盈止损执行",
    },
    "position_quality": {
        "key": "position_quality",
        "label_zh": "仓位质量",
        "label_en": "Position Quality",
        "max_score": 15,
        "description": "仓位大小、加减仓节奏、资金利用率",
    },
    "holding_period": {
        "key": "holding_period",
        "label_zh": "持仓周期",
        "label_en": "Holding Period",
        "max_score": 5,
        "description": "持仓时长是否与策略匹配",
    },
    "risk_control": {
        "key": "risk_control",
        "label_zh": "风险控制",
        "label_en": "Risk Control",
        "max_score": 10,
        "description": "止损执行、最大回撤控制、逆势加仓纪律",
    },
    "decision_attribution": {
        "key": "decision_attribution",
        "label_zh": "决策归因",
        "label_en": "Decision Attribution",
        "max_score": 5,
        "description": "决策逻辑清晰度、是否有系统化规则",
    },
}

TRADE_REVIEW_TOTAL_MAX = 100

# ---------------------------------------------------------------------------
# Rating thresholds
# ---------------------------------------------------------------------------

RATING_THRESHOLDS: list[tuple[float, str, str]] = [
    (85, "excellent", "优秀"),
    (70, "good", "良好"),
    (50, "fair", "一般"),
    (0, "poor", "较差"),
]


def compute_rating(score: float) -> tuple[str, str]:
    """Return (rating_en, rating_zh) for a given overall score."""
    for threshold, rating_en, rating_zh in RATING_THRESHOLDS:
        if score >= threshold:
            return rating_en, rating_zh
    return "poor", "较差"
