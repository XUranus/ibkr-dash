"""Daily position review eval cases."""

from app.agents.eval_harness import EvalCase


CASES = [
    EvalCase(
        case_id="daily_review_account_attribution_before_news",
        agent_name="daily_position_review",
        title="Account attribution should come before news narrative",
        tags=["attribution", "account_first"],
        input={"report_date": "2026-05-20"},
        expected_output_fields=["summary", "account_conclusion", "data_limitations"],
    ),
    EvalCase(
        case_id="daily_review_public_data_missing_limitations",
        agent_name="daily_position_review",
        title="Missing public data must include data_limitations",
        tags=["data_missing"],
        input={"report_date": "2026-05-21"},
        expected_behavior={"data_missing": True},
        expected_output_fields=["summary", "data_limitations"],
    ),
    EvalCase(
        case_id="daily_review_small_move_no_over_attribution",
        agent_name="daily_position_review",
        title="Small daily move must not be over-attributed to single news",
        tags=["attribution", "small_move"],
        input={"report_date": "2026-05-22"},
        expected_output_fields=["summary", "data_limitations"],
        forbidden_behavior=["sole reason", "entirely because of"],
    ),
    EvalCase(
        case_id="daily_review_mstr_no_btc_without_data",
        agent_name="daily_position_review",
        title="MSTR without BTC data must not attribute to BTC",
        tags=["mstr", "btc", "data_missing"],
        input={"report_date": "2026-05-23", "symbol": "MSTR.US"},
        expected_behavior={"data_missing": True},
        expected_output_fields=["summary", "data_limitations"],
    ),
]
