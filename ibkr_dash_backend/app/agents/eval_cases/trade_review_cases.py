"""Trade review eval cases."""

from app.agents.eval_harness import EvalCase


CASES = [
    EvalCase(
        case_id="trade_review_buy_only_open_position_not_zero",
        agent_name="trade_review",
        title="BUY-only open position must not be zeroed just because no SELL",
        tags=["buy_only", "open_position"],
        input={"review_type": "single_trade_review", "trade_id": "sample-buy-only"},
        expected_behavior={"data_missing": False},
        expected_output_fields=["summary", "overall_score", "rating", "data_limitations"],
    ),
    EvalCase(
        case_id="trade_review_profit_but_chase_high_not_excellent",
        agent_name="trade_review",
        title="Profitable but chased high must not be rated excellent just for profit",
        tags=["chase_high", "scoring"],
        input={"symbol": "NVDA.US"},
        expected_output_fields=["summary", "overall_score", "rating", "mistake_tags"],
        forbidden_behavior=["profitable means good trade"],
    ),
    EvalCase(
        case_id="trade_review_loss_but_disciplined_not_poor",
        agent_name="trade_review",
        title="Loss but disciplined must not be rated poor just for loss",
        tags=["loss", "discipline"],
        input={"symbol": "AMD.US"},
        expected_output_fields=["summary", "overall_score", "rating", "data_limitations"],
    ),
    EvalCase(
        case_id="trade_review_sold_too_early_avoid_hindsight",
        agent_name="trade_review",
        title="Sold too early can note opportunity cost but avoid hindsight bias",
        tags=["opportunity_cost", "hindsight"],
        input={"symbol": "TSLA.US"},
        expected_output_fields=["summary", "mistake_tags", "data_limitations"],
        forbidden_behavior=["completely deny the sell decision"],
    ),
]
