export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '--'
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

export function formatPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '--'
  return `${formatNumber(value, digits)}%`
}

export function formatSignedNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '--'
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${formatNumber(value, digits)}`
}

export function formatSignedPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return '--'
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${formatNumber(value, digits)}%`
}

export function pnlClass(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) return 'table-pnl--neutral'
  return value > 0 ? 'table-pnl--positive' : 'table-pnl--negative'
}

export function toneClass(value: number | null | undefined): 'positive' | 'negative' | 'neutral' {
  if (!value) return 'neutral'
  return value > 0 ? 'positive' : 'negative'
}
