"""Chart service: equity curve and performance calendar.

Builds time-series data from account_snapshots, trade_records, and cash_flows.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta

from app.core.database import Database
from app.schemas.charts import (
    EquityCurvePoint,
    EquityCurveResponse,
    PerformanceCalendarItem,
    PerformanceCalendarResponse,
    PerformanceCalendarSummary,
)
from app.utils.dates import parse_date

INFERRED_DAILY_PNL_EPSILON = 0.01
DEPOSIT_WITHDRAWAL_FLOW_TYPE = "Deposits/Withdrawals"
CURVE_AMOUNT_PRECISION = 2
CURVE_PERCENT_PRECISION = 2
PERFORMANCE_CALENDAR_VIEWS = {"month", "year", "all-years"}


@dataclass
class DailyPerformanceEntry:
    report_date: date
    daily_mtm: float | None
    daily_twr: float | None


class ChartService:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Equity curve
    # ------------------------------------------------------------------

    def get_equity_curve(self, start_date: str | None, end_date: str | None) -> EquityCurveResponse:
        """Build the equity curve time series."""
        latest_report_date = self._get_latest_report_date()
        if latest_report_date is None:
            return EquityCurveResponse(items=[])

        effective_end = parse_date(end_date) or latest_report_date
        effective_start = parse_date(start_date)

        # Fetch ALL snapshots from the beginning (not just the requested range)
        # so cumulative PnL and net_cost are computed correctly.
        # We filter for display later.
        snapshot_rows = self.db.execute(
            """
            SELECT account_id, report_date, total_equity, cnav_mtm, cnav_twr, cnav_deposits,
                   cnav_realized, cnav_change_in_unrealized
            FROM account_snapshots
            WHERE report_date <= ?
            ORDER BY report_date ASC
            """,
            (effective_end.isoformat(),),
        )
        if not snapshot_rows:
            return EquityCurveResponse(items=[])

        account_id = snapshot_rows[-1].get("account_id")

        # Build cash flow net-cost curve and daily net flows
        cash_flow_rows = self._fetch_cash_flows(account_id, effective_end, effective_start)
        cash_flow_curve = self._build_net_cost_curve(cash_flow_rows)
        daily_net_flows = self._build_daily_net_flows(cash_flow_rows)

        # Build realized PnL curve
        realized_pnl_curve = self._build_realized_pnl_curve(account_id, effective_end)

        # Determine if cash flow data has real values
        cash_flows_have_value = any(abs(p[1]) > 0.01 for p in cash_flow_curve) if cash_flow_curve else False

        latest_calendar_month = effective_end.strftime("%Y-%m")

        items: list[EquityCurvePoint] = []
        current_net_cost = 0.0
        current_realized_pnl = 0.0
        cash_flow_index = 0
        realized_pnl_index = 0
        previous_total_equity: float | None = None
        cumulative_market_pnl = 0.0  # TWR-based cumulative PnL (excludes deposits)

        for source in snapshot_rows:
            report_date = source["report_date"]
            total_equity = source.get("total_equity")

            # Advance cash flow pointer
            if cash_flows_have_value:
                while cash_flow_index < len(cash_flow_curve) and cash_flow_curve[cash_flow_index][0] <= report_date:
                    current_net_cost = cash_flow_curve[cash_flow_index][1]
                    cash_flow_index += 1
            while realized_pnl_index < len(realized_pnl_curve) and realized_pnl_curve[realized_pnl_index][0] <= report_date:
                current_realized_pnl = realized_pnl_curve[realized_pnl_index][1]
                realized_pnl_index += 1

            twr = source.get("cnav_twr")
            cumulative_mtm = source.get("cnav_mtm")
            deposits = source.get("cnav_deposits") or 0.0
            change_in_unrealized = source.get("cnav_change_in_unrealized")
            realized = source.get("cnav_realized")

            # Compute daily MTM
            daily_mtm = None
            daily_mtm_inferred = False

            detail_pnl = (float(change_in_unrealized or 0) + float(realized or 0))
            detail_fields_populated = (
                change_in_unrealized is not None
                and realized is not None
                and not (detail_pnl == 0.0 and twr is not None and float(twr) != 0.0)
            )
            if detail_fields_populated:
                daily_mtm = detail_pnl
            elif twr is not None and previous_total_equity is not None and previous_total_equity != 0:
                daily_mtm = float(previous_total_equity) * float(twr) / 100.0
                daily_mtm_inferred = True
            elif cumulative_mtm is not None and previous_total_equity is not None:
                daily_mtm = float(cumulative_mtm) - float(deposits)
            elif cumulative_mtm is None and total_equity is not None and previous_total_equity is not None:
                daily_mtm = float(total_equity) - float(previous_total_equity) - daily_net_flows.get(report_date, 0.0)
                daily_mtm_inferred = True
                if abs(float(daily_mtm)) < INFERRED_DAILY_PNL_EPSILON:
                    daily_mtm = 0.0

            daily_twr = None
            if daily_mtm is not None:
                daily_twr = twr
                if daily_twr is None and previous_total_equity not in (None, 0, 0.0):
                    daily_twr = float(daily_mtm) / abs(float(previous_total_equity)) * 100.0
                if daily_mtm_inferred and daily_mtm == 0.0:
                    daily_twr = 0.0

            # Accumulate TWR-based market PnL (excludes deposit effects)
            if daily_mtm is not None:
                cumulative_market_pnl += float(daily_mtm)

            # Compute net_cost and total_pnl
            if cash_flows_have_value:
                # Use actual cash flow data (ibkr-show-public approach)
                net_cost = current_net_cost
            else:
                # Derive net_cost from TWR-based cumulative PnL:
                # net_cost = total_equity - cumulative_market_pnl
                # This automatically increases when deposits arrive (equity rises, PnL doesn't)
                net_cost = float(total_equity or 0) - cumulative_market_pnl if total_equity is not None else 0.0

            total_pnl = None
            if total_equity is not None:
                total_pnl = float(total_equity) - float(net_cost)

            # Only show daily MTM/TWR for the latest calendar month
            if not report_date.startswith(latest_calendar_month):
                daily_mtm = None
                daily_twr = None

            # Only include items within the requested display range
            if effective_start is None or report_date >= effective_start.isoformat():
                items.append(EquityCurvePoint(
                    report_date=report_date,
                    total_equity=self._round_amount(total_equity),
                    total_pnl=self._round_amount(total_pnl),
                    net_cost=self._round_amount(net_cost),
                    realized_pnl=self._round_amount(current_realized_pnl),
                    daily_mtm=self._round_amount(daily_mtm),
                    daily_twr=self._round_percent(daily_twr),
                ))
            previous_total_equity = float(total_equity) if total_equity is not None else previous_total_equity

        return EquityCurveResponse(items=items)

    # ------------------------------------------------------------------
    # Performance calendar
    # ------------------------------------------------------------------

    def get_performance_calendar(self, view: str, anchor: str | None) -> PerformanceCalendarResponse:
        """Build performance calendar for month/year/all-years views."""
        if view not in PERFORMANCE_CALENDAR_VIEWS:
            raise ValueError("view must be one of: month, year, all-years")

        latest_report_date = self._get_latest_report_date()
        if latest_report_date is None:
            return PerformanceCalendarResponse(
                view=view, anchor=anchor or "", latest_anchor="",
                earliest_anchor=None, items=[], summary=PerformanceCalendarSummary(),
            )

        latest_month_anchor = latest_report_date.strftime("%Y-%m")
        latest_year_anchor = latest_report_date.strftime("%Y")
        effective_anchor = anchor or (
            latest_month_anchor if view == "month"
            else latest_year_anchor if view == "year"
            else "all"
        )

        earliest_report_date = self._get_earliest_report_date() or latest_report_date

        if view == "month":
            return self._build_month_calendar_response(
                latest_report_date=latest_report_date,
                latest_anchor=latest_month_anchor,
                earliest_report_date=earliest_report_date,
                anchor=effective_anchor,
            )
        elif view == "year":
            return self._build_year_calendar_response(
                latest_report_date=latest_report_date,
                latest_anchor=latest_year_anchor,
                earliest_report_date=earliest_report_date,
                anchor=effective_anchor,
            )
        else:
            return self._build_all_years_calendar_response(
                latest_report_date=latest_report_date,
                earliest_report_date=earliest_report_date,
            )

    # ------------------------------------------------------------------
    # Calendar builders
    # ------------------------------------------------------------------

    def _build_month_calendar_response(
        self,
        *,
        latest_report_date: date,
        latest_anchor: str,
        earliest_report_date: date,
        anchor: str,
    ) -> PerformanceCalendarResponse:
        effective_month = self._parse_month_anchor(anchor)
        latest_month = date(latest_report_date.year, latest_report_date.month, 1)
        earliest_month = date(earliest_report_date.year, earliest_report_date.month, 1)
        effective_month = min(max(effective_month, earliest_month), latest_month)

        start = effective_month
        end = min(self._month_end(effective_month), latest_report_date)
        entries = self._build_daily_performance_entries(start, end)
        entries_by_date = {entry.report_date.isoformat(): entry for entry in entries}
        days_in_month = monthrange(effective_month.year, effective_month.month)[1]

        items: list[PerformanceCalendarItem] = []
        for day in range(1, days_in_month + 1):
            period_date = date(effective_month.year, effective_month.month, day)
            entry = entries_by_date.get(period_date.isoformat())
            items.append(PerformanceCalendarItem(
                period_key=period_date.isoformat(),
                label=str(day),
                period_start=period_date.isoformat(),
                pnl=entry.daily_mtm if entry else None,
                twr=entry.daily_twr if entry else None,
                has_data=entry is not None and entry.daily_mtm is not None,
            ))

        return PerformanceCalendarResponse(
            view="month",
            anchor=effective_month.strftime("%Y-%m"),
            latest_anchor=latest_anchor,
            earliest_anchor=earliest_month.strftime("%Y-%m"),
            previous_anchor=(
                (effective_month - timedelta(days=1)).strftime("%Y-%m")
                if effective_month > earliest_month else None
            ),
            next_anchor=(
                (self._month_end(effective_month) + timedelta(days=1)).strftime("%Y-%m")
                if effective_month < latest_month else None
            ),
            items=items,
            summary=self._build_calendar_summary(items),
        )

    def _build_year_calendar_response(
        self,
        *,
        latest_report_date: date,
        latest_anchor: str,
        earliest_report_date: date,
        anchor: str,
    ) -> PerformanceCalendarResponse:
        effective_year = self._parse_year_anchor(anchor)
        earliest_year = earliest_report_date.year
        latest_year = latest_report_date.year
        effective_year = min(max(effective_year, earliest_year), latest_year)

        start = date(effective_year, 1, 1)
        end = min(date(effective_year, 12, 31), latest_report_date)
        entries = self._build_daily_performance_entries(start, end)

        items: list[PerformanceCalendarItem] = []
        for month_num in range(1, 13):
            month_start = date(effective_year, month_num, 1)
            month_end = self._month_end(month_start)
            month_entries = [e for e in entries if month_start <= e.report_date <= month_end]
            items.append(self._build_grouped_calendar_item(
                period_key=f"{effective_year}-{month_num:02d}",
                label=f"{month_num}M",
                period_start=month_start.isoformat(),
                period_end=month_end.isoformat(),
                entries=month_entries,
            ))

        return PerformanceCalendarResponse(
            view="year",
            anchor=str(effective_year),
            latest_anchor=latest_anchor,
            earliest_anchor=str(earliest_year),
            previous_anchor=str(effective_year - 1) if effective_year > earliest_year else None,
            next_anchor=str(effective_year + 1) if effective_year < latest_year else None,
            items=items,
            summary=self._build_calendar_summary(items),
        )

    def _build_all_years_calendar_response(
        self,
        *,
        latest_report_date: date,
        earliest_report_date: date,
    ) -> PerformanceCalendarResponse:
        entries = self._build_daily_performance_entries(None, latest_report_date)

        items: list[PerformanceCalendarItem] = []
        for year in range(earliest_report_date.year, latest_report_date.year + 1):
            year_start = date(year, 1, 1)
            year_end = date(year, 12, 31)
            year_entries = [e for e in entries if year_start <= e.report_date <= year_end]
            items.append(self._build_grouped_calendar_item(
                period_key=str(year),
                label=f"{year}",
                period_start=year_start.isoformat(),
                period_end=year_end.isoformat(),
                entries=year_entries,
            ))

        return PerformanceCalendarResponse(
            view="all-years",
            anchor="all",
            latest_anchor=str(latest_report_date.year),
            earliest_anchor=str(earliest_report_date.year),
            items=items,
            summary=self._build_calendar_summary(items),
        )

    # ------------------------------------------------------------------
    # Performance helpers
    # ------------------------------------------------------------------

    def _build_daily_performance_entries(
        self, start: date | None, end: date
    ) -> list[DailyPerformanceEntry]:
        """Compute daily MTM and TWR entries for a date range."""
        conditions = ["report_date <= ?"]
        params: list = [end.isoformat()]
        if start:
            conditions.append("report_date >= ?")
            params.append(start.isoformat())
        where_clause = " AND ".join(conditions)

        snapshot_rows = self.db.execute(
            f"""
            SELECT account_id, report_date, total_equity, cnav_mtm, cnav_twr, cnav_deposits,
                   cnav_realized, cnav_change_in_unrealized
            FROM account_snapshots
            WHERE {where_clause}
            ORDER BY report_date ASC
            """,
            tuple(params),
        )
        if not snapshot_rows:
            return []

        account_id = snapshot_rows[0].get("account_id") or snapshot_rows[-1].get("account_id")

        # Get previous snapshot before start for daily MTM/TWR calculation
        previous_total_equity: float | None = None
        previous_cumulative_mtm: float | None = None
        if start is not None:
            prev_row = self.db.execute_one(
                """
                SELECT total_equity, cnav_mtm FROM account_snapshots
                WHERE report_date < ? ORDER BY report_date DESC LIMIT 1
                """,
                (start.isoformat(),),
            )
            if prev_row:
                if prev_row.get("total_equity") is not None:
                    previous_total_equity = float(prev_row["total_equity"])
                if prev_row.get("cnav_mtm") is not None:
                    previous_cumulative_mtm = float(prev_row["cnav_mtm"])

        entries: list[DailyPerformanceEntry] = []
        for source in snapshot_rows:
            rd = parse_date(source["report_date"])
            total_equity = source.get("total_equity")
            cumulative_mtm = source.get("cnav_mtm")
            deposits = source.get("cnav_deposits") or 0.0
            change_in_unrealized = source.get("cnav_change_in_unrealized")
            realized = source.get("cnav_realized")

            daily_mtm = None
            daily_mtm_inferred = False
            twr = source.get("cnav_twr")

            # Primary: use changeInUnrealized + realized from ChangeInNAV
            # This is the most reliable source for daily PnL.
            # But IBKR's real-time API sometimes zeroes these fields while
            # leaving TWR non-zero; detect and skip that case.
            detail_pnl = (float(change_in_unrealized or 0) + float(realized or 0))
            detail_fields_populated = (
                change_in_unrealized is not None
                and realized is not None
                and not (detail_pnl == 0.0 and twr is not None and float(twr) != 0.0)
            )
            if detail_fields_populated:
                daily_mtm = detail_pnl
            elif twr is not None and previous_total_equity is not None and previous_total_equity != 0:
                # Fallback: derive from TWR and previous equity.
                # More reliable than cumulative subtraction when deposits are unknown
                # (IBKR real-time API zeroes out depositsWithdrawals).
                daily_mtm = float(previous_total_equity) * float(twr) / 100.0
                daily_mtm_inferred = True
            elif cumulative_mtm is not None and previous_cumulative_mtm is not None:
                # Fallback: cumulative difference minus deposits
                daily_mtm = float(cumulative_mtm) - float(previous_cumulative_mtm) - float(deposits)
            elif cumulative_mtm is None and total_equity is not None and previous_total_equity is not None:
                # Last resort: infer from equity change
                daily_mtm = float(total_equity) - float(previous_total_equity) - float(deposits)
                daily_mtm_inferred = True
                if abs(float(daily_mtm)) < INFERRED_DAILY_PNL_EPSILON:
                    daily_mtm = 0.0

            daily_twr = None
            if daily_mtm is not None:
                daily_twr = twr
                if daily_twr is None and previous_total_equity not in (None, 0, 0.0):
                    daily_twr = float(daily_mtm) / abs(float(previous_total_equity)) * 100.0
                if daily_mtm_inferred and daily_mtm == 0.0:
                    daily_twr = 0.0

            entries.append(DailyPerformanceEntry(
                report_date=rd,
                daily_mtm=self._round_amount(daily_mtm),
                daily_twr=self._round_percent(daily_twr),
            ))
            if total_equity is not None:
                previous_total_equity = float(total_equity)
            if cumulative_mtm is not None:
                previous_cumulative_mtm = float(cumulative_mtm)

        return entries

    @staticmethod
    def _build_grouped_calendar_item(
        *,
        period_key: str,
        label: str,
        period_start: str,
        period_end: str,
        entries: list[DailyPerformanceEntry],
    ) -> PerformanceCalendarItem:
        if not entries:
            return PerformanceCalendarItem(
                period_key=period_key, label=label,
                period_start=period_start, period_end=period_end,
                has_data=False,
            )

        total_pnl = sum(e.daily_mtm or 0.0 for e in entries if e.daily_mtm is not None)
        twr = ChartService._compound_twr_static([e.daily_twr for e in entries if e.daily_twr is not None])
        return PerformanceCalendarItem(
            period_key=period_key, label=label,
            period_start=period_start, period_end=period_end,
            pnl=round(total_pnl, CURVE_AMOUNT_PRECISION),
            twr=round(twr, CURVE_PERCENT_PRECISION) if twr is not None else None,
            has_data=True,
        )

    @staticmethod
    def _build_calendar_summary(items: list[PerformanceCalendarItem]) -> PerformanceCalendarSummary:
        positive = 0
        negative = 0
        total_pnl = 0.0
        with_data = 0
        for item in items:
            if item.pnl is None:
                continue
            with_data += 1
            total_pnl += item.pnl
            if item.pnl > 0:
                positive += 1
            elif item.pnl < 0:
                negative += 1
        return PerformanceCalendarSummary(
            positive_periods=positive,
            negative_periods=negative,
            total_pnl=round(total_pnl, CURVE_AMOUNT_PRECISION) if with_data else None,
            periods_with_data=with_data,
        )

    @staticmethod
    def _compound_twr_static(values: list[float]) -> float | None:
        if not values:
            return None
        cumulative = 1.0
        for v in values:
            cumulative *= 1.0 + float(v) / 100.0
        return (cumulative - 1.0) * 100.0

    # ------------------------------------------------------------------
    # Cash flow helpers
    # ------------------------------------------------------------------

    def _fetch_cash_flows(
        self, account_id: str, end: date, start: date | None = None
    ) -> list[dict]:
        conditions = ["account_id = ?", "flow_type = ?", "date_time <= ?"]
        params: list = [account_id, DEPOSIT_WITHDRAWAL_FLOW_TYPE, end.isoformat()]
        if start:
            conditions.append("date_time >= ?")
            params.append(start.isoformat())
        where_clause = " AND ".join(conditions)
        return self.db.execute(
            f"""
            SELECT date_time, settle_date, amount_in_base
            FROM cash_flows
            WHERE {where_clause}
            ORDER BY date_time ASC
            """,
            tuple(params),
        )

    @staticmethod
    def _build_net_cost_curve(cash_flow_rows: list[dict]) -> list[tuple[str, float]]:
        cumulative = 0.0
        points: list[tuple[str, float]] = []
        for row in cash_flow_rows:
            effective_date = row.get("settle_date")
            if not effective_date:
                dt = row.get("date_time")
                if dt:
                    effective_date = str(dt).split("T", 1)[0]
            if not effective_date:
                continue
            cumulative += float(row.get("amount_in_base") or 0.0)
            if points and points[-1][0] == effective_date:
                points[-1] = (effective_date, cumulative)
            else:
                points.append((effective_date, cumulative))
        return points

    @staticmethod
    def _build_daily_net_flows(cash_flow_rows: list[dict]) -> dict[str, float]:
        flows: dict[str, float] = {}
        for row in cash_flow_rows:
            effective_date = row.get("settle_date")
            if not effective_date:
                dt = row.get("date_time")
                if dt:
                    effective_date = str(dt).split("T", 1)[0]
            if not effective_date:
                continue
            flows[effective_date] = flows.get(effective_date, 0.0) + float(row.get("amount_in_base") or 0.0)
        return flows

    def _build_realized_pnl_curve(
        self, account_id: str | None, effective_end: date
    ) -> list[tuple[str, float]]:
        if not account_id:
            return []
        rows = self.db.execute(
            """
            SELECT trade_date, fifo_pnl_realized
            FROM trade_records
            WHERE trade_date <= ?
            ORDER BY trade_date ASC
            """,
            (effective_end.isoformat(),),
        )
        cumulative = 0.0
        points: list[tuple[str, float]] = []
        for row in rows:
            td = row.get("trade_date")
            if not td:
                continue
            cumulative += float(row.get("fifo_pnl_realized") or 0.0)
            if points and points[-1][0] == td:
                points[-1] = (td, cumulative)
            else:
                points.append((td, cumulative))
        return points

    # ------------------------------------------------------------------
    # Date helpers
    # ------------------------------------------------------------------

    def _get_latest_report_date(self) -> date | None:
        row = self.db.execute_one(
            "SELECT report_date FROM account_snapshots ORDER BY report_date DESC LIMIT 1"
        )
        return parse_date(row["report_date"]) if row else None

    def _get_earliest_report_date(self) -> date | None:
        row = self.db.execute_one(
            "SELECT report_date FROM account_snapshots ORDER BY report_date ASC LIMIT 1"
        )
        return parse_date(row["report_date"]) if row else None

    @staticmethod
    def _parse_month_anchor(value: str) -> date:
        try:
            year_text, month_text = value.split("-")
            return date(int(year_text), int(month_text), 1)
        except ValueError as exc:
            raise ValueError("month anchor must use YYYY-MM format") from exc

    @staticmethod
    def _parse_year_anchor(value: str) -> int:
        if len(value) != 4 or not value.isdigit():
            raise ValueError("year anchor must use YYYY format")
        return int(value)

    @staticmethod
    def _month_end(value: date) -> date:
        return date(value.year, value.month, monthrange(value.year, value.month)[1])

    @staticmethod
    def _round_amount(value: float | None) -> float | None:
        if value is None:
            return None
        return round(float(value), CURVE_AMOUNT_PRECISION)

    @staticmethod
    def _round_percent(value: float | None) -> float | None:
        if value is None:
            return None
        return round(float(value), CURVE_PERCENT_PRECISION)
