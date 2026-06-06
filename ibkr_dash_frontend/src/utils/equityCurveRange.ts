export type EquityCurveRangeKey = 'ytd' | 'all' | '1y' | '6m' | '3m' | '1m'

export type EquityCurveRangeOption = {
  key: EquityCurveRangeKey
  label: string
}

export const EQUITY_CURVE_RANGE_OPTIONS: EquityCurveRangeOption[] = [
  { key: 'ytd', label: 'dashboard.rangeYearToDate' },
  { key: 'all', label: 'dashboard.rangeAll' },
  { key: '1y', label: 'dashboard.range1Year' },
  { key: '6m', label: 'dashboard.range6Months' },
  { key: '3m', label: 'dashboard.range3Months' },
  { key: '1m', label: 'dashboard.range1Month' },
]

export function buildEquityCurveRangeParams(
  reportDate: string | null | undefined,
  range: EquityCurveRangeKey,
): { start_date?: string; end_date?: string } {
  if (!reportDate || range === 'all') return {}

  if (range === 'ytd') {
    const year = reportDate.slice(0, 4)
    return { start_date: `${year}-01-01`, end_date: reportDate }
  }

  const parsed = new Date(`${reportDate}T00:00:00Z`)
  if (Number.isNaN(parsed.getTime())) return {}

  const start = new Date(parsed)
  if (range === '1y') start.setUTCFullYear(start.getUTCFullYear() - 1)
  else if (range === '6m') start.setUTCMonth(start.getUTCMonth() - 6)
  else if (range === '3m') start.setUTCMonth(start.getUTCMonth() - 3)
  else if (range === '1m') start.setUTCMonth(start.getUTCMonth() - 1)

  return {
    start_date: formatDate(start),
    end_date: reportDate,
  }
}

function formatDate(value: Date): string {
  const year = value.getUTCFullYear()
  const month = String(value.getUTCMonth() + 1).padStart(2, '0')
  const day = String(value.getUTCDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
