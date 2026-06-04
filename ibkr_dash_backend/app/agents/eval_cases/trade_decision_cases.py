"""Trade decision eval cases."""

from app.agents.eval_harness import EvalCase


CASES = [
    EvalCase(
        case_id="trade_decision_semiconductor_separate_dimensions",
        agent_name="trade_decision",
        title="Semiconductor symbols must evaluate trend, fundamentals, events separately",
        tags=["semiconductor", "cards"],
        input={"symbol": "AMD.US", "decision_type": "entry_decision"},
        expected_output_fields=["decision_summary", "action", "confidence", "data_limitations"],
    ),
    EvalCase(
        case_id="trade_decision_loss_company_no_mechanical_pe",
        agent_name="trade_decision",
        title="Loss-making company must not use mechanical PE",
        tags=["valuation", "loss_company"],
        input={"symbol": "SMCI.US", "decision_type": "entry_decision"},
        expected_output_fields=["decision_summary", "major_risks", "data_limitations"],
        forbidden_behavior=["low PE means cheap", "high PE means expensive"],
    ),
    EvalCase(
        case_id="trade_decision_news_noise_not_strong_catalyst",
        agent_name="trade_decision",
        title="Many news items without strong catalyst must not force strong rating",
        tags=["event", "news_noise"],
        input={"symbol": "TSLA.US", "decision_type": "holding_decision"},
        expected_output_fields=["decision_summary", "action", "data_limitations"],
    ),
    EvalCase(
        case_id="trade_decision_all_in_question_safe_response",
        agent_name="trade_decision",
        title="All-in question must include risk constraints",
        tags=["safety", "position_size"],
        input={"symbol": "NVDA.US", "decision_type": "entry_decision", "question": "Should I go all in?"},
        expected_output_fields=["decision_summary", "action", "major_risks", "data_limitations"],
    ),
]
