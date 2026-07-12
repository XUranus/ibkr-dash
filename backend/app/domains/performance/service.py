"""Account performance service -- computes TWR from account snapshots and cash flows."""

from __future__ import annotations

import logging
import math
from datetime import datetime

from app.core.database import Database
from app.domains.performance.schemas import (
    AccountPerformancePoint,
    AccountPerformanceSummary,
    AccountPerformanceDataQuality,
    PerformanceMethodology,
    PerformanceSeriesResponse,
)

logger = logging.getLogger(__name__)


class AccountPerformanceService:
    """Compute time-weighted return from account snapshots and cash flows."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def get_series(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        base_index: float = 100.0,
    ) -> PerformanceSeriesResponse:
        """Build a performance series with TWR calculation."""
        # Get account snapshots ordered by date
        snapshots = self._get_snapshots(start_date, end_date)
        if not snapshots:
            summary = AccountPerformanceSummary(
                start_date=start_date,
                end_date=end_date,
                data_quality="missing",
                data_limitations=["account_nav_source_missing"],
            )
            return PerformanceSeriesResponse(
                summary=summary,
                series=[],
                methodology=PerformanceMethodology(base_index=base_index),
            )

        # Get cash flows for the period
        cashflows = self._get_cashflows(start_date, end_date)
        cf_by_date = _group_cashflows_by_date(cashflows)

        # Build series with TWR
        series: list[AccountPerformancePoint] = []
        prev_nav: float | None = None
        twr_cumulative = base_index
        limitations: list[str] = []

        for snap in snapshots:
            report_date = snap["report_date"]
            nav = snap.get("total_equity") or 0.0
            net_cf = cf_by_date.get(report_date, 0.0)

            # Daily return = (NAV - net_CF - prev_NAV) / prev_NAV
            if prev_nav is not None and prev_nav > 0:
                adjusted_nav = nav - net_cf
                daily_return = (adjusted_nav - prev_nav) / prev_nav
                twr_cumulative *= (1 + daily_return)
            else:
                daily_return = None

            investment_pnl = None
            if prev_nav is not None:
                investment_pnl = nav - prev_nav - net_cf

            series.append(AccountPerformancePoint(
                date=report_date,
                nav=round(nav, 2),
                net_cash_flow=round(net_cf, 2),
                investment_pnl=round(investment_pnl, 2) if investment_pnl is not None else None,
                daily_return=round(daily_return, 6) if daily_return is not None else None,
                twr_index=round(twr_cumulative, 4),
                data_quality="complete",
            ))
            prev_nav = nav

        # Compute summary
        summary = self._compute_summary(series, base_index, limitations)

        return PerformanceSeriesResponse(
            summary=summary,
            series=series,
            methodology=PerformanceMethodology(base_index=base_index),
        )

    def get_summary(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        base_index: float = 100.0,
    ) -> AccountPerformanceSummary:
        """Get only the summary portion of the performance series."""
        return self.get_series(
            start_date=start_date, end_date=end_date, base_index=base_index
        ).summary

    def _get_snapshots(self, start_date: str | None, end_date: str | None) -> list[dict]:
        """Get account snapshots ordered by date."""
        conditions = []
        params: list = []
        if start_date:
            conditions.append("report_date >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("report_date <= ?")
            params.append(end_date)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.db.execute(
            f"SELECT * FROM account_snapshots {where} ORDER BY report_date ASC",
            tuple(params),
        )

    def _get_cashflows(self, start_date: str | None, end_date: str | None) -> list[dict]:
        """Get cash flows for the period."""
        conditions = []
        params: list = []
        if start_date:
            conditions.append("date_time >= ?")
            params.append(start_date)
        if end_date:
            conditions.append("date_time <= ?")
            params.append(end_date)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.db.execute(
            f"SELECT * FROM cash_flows {where} ORDER BY date_time ASC",
            tuple(params),
        )

    @staticmethod
    def _compute_summary(
        series: list[AccountPerformancePoint],
        base_index: float,
        limitations: list[str],
    ) -> AccountPerformanceSummary:
        """Compute summary statistics from the performance series."""
        if not series:
            return AccountPerformanceSummary(
                data_quality="missing",
                data_limitations=limitations or ["account_nav_source_missing"],
            )

        start_nav = series[0].nav
        end_nav = series[-1].nav
        start_date = series[0].date
        end_date = series[-1].date

        total_cf = sum(p.net_cash_flow for p in series)
        money_gain = (end_nav - start_nav - total_cf) if (end_nav is not None and start_nav is not None) else None

        # TWR total return
        twr_total = None
        if series[-1].twr_index is not None:
            twr_total = (series[-1].twr_index / base_index) - 1.0

        # Annualized return
        annualized = None
        if twr_total is not None and len(series) > 1:
            try:
                d0 = datetime.fromisoformat(series[0].date)
                d1 = datetime.fromisoformat(series[-1].date)
                days = (d1 - d0).days
                if days > 0:
                    annualized = (1 + twr_total) ** (365.0 / days) - 1.0
            except (ValueError, TypeError):
                pass

        # Max drawdown
        max_dd = _compute_max_drawdown(series)

        # Volatility and Sharpe
        volatility, sharpe = _compute_volatility_sharpe(series)

        data_quality: AccountPerformanceDataQuality = "complete" if not limitations else "partial"

        return AccountPerformanceSummary(
            start_date=start_date,
            end_date=end_date,
            start_nav=start_nav,
            end_nav=end_nav,
            total_net_cash_flow=round(total_cf, 2),
            money_gain=round(money_gain, 2) if money_gain is not None else None,
            twr_total_return=round(twr_total, 6) if twr_total is not None else None,
            annualized_return=round(annualized, 6) if annualized is not None else None,
            max_drawdown=round(max_dd, 6) if max_dd is not None else None,
            volatility=round(volatility, 6) if volatility is not None else None,
            sharpe_ratio=round(sharpe, 4) if sharpe is not None else None,
            data_quality=data_quality,
            data_limitations=limitations,
        )


def _group_cashflows_by_date(cashflows: list[dict]) -> dict[str, float]:
    """Group cash flows by date, summing amounts."""
    result: dict[str, float] = {}
    for cf in cashflows:
        dt = (cf.get("date_time") or "")[:10]
        if not dt:
            continue
        amount = cf.get("amount_in_base") or cf.get("amount") or 0.0
        result[dt] = result.get(dt, 0.0) + amount
    return result


def _compute_max_drawdown(series: list[AccountPerformancePoint]) -> float | None:
    """Compute max drawdown from TWR index."""
    indices = [p.twr_index for p in series if p.twr_index is not None]
    if len(indices) < 2:
        return None
    peak = indices[0]
    max_dd = 0.0
    for idx in indices:
        if idx > peak:
            peak = idx
        dd = (peak - idx) / peak
        if dd > max_dd:
            max_dd = dd
    return -max_dd if max_dd > 0 else 0.0


def _compute_volatility_sharpe(series: list[AccountPerformancePoint]) -> tuple[float | None, float | None]:
    """Compute annualized volatility and Sharpe ratio from daily returns."""
    returns = [p.daily_return for p in series if p.daily_return is not None]
    if len(returns) < 10:
        return None, None

    mean_r = sum(returns) / len(returns)
    var = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    daily_vol = math.sqrt(var) if var > 0 else 0.0
    annual_vol = daily_vol * math.sqrt(252)

    # Sharpe = annualized_return / annualized_volatility (assuming 0 risk-free rate)
    annualized_return = mean_r * 252
    sharpe = annualized_return / annual_vol if annual_vol > 0 else None

    return annual_vol, sharpe
