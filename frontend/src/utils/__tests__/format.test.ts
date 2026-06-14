import { describe, it, expect } from 'vitest'
import {
  formatNumber,
  formatPercent,
  formatSignedNumber,
  formatSignedPercent,
  pnlClass,
  toneClass,
} from '../format'

describe('formatNumber', () => {
  it('formats a positive number with default 2 decimals', () => {
    expect(formatNumber(1234.567)).toBe('1,234.57')
  })

  it('formats a negative number', () => {
    expect(formatNumber(-9876.5)).toBe('-9,876.50')
  })

  it('formats zero', () => {
    expect(formatNumber(0)).toBe('0.00')
  })

  it('returns "--" for null', () => {
    expect(formatNumber(null)).toBe('--')
  })

  it('returns "--" for undefined', () => {
    expect(formatNumber(undefined)).toBe('--')
  })

  it('respects custom digit count', () => {
    expect(formatNumber(1234.5678, 3)).toBe('1,234.568')
  })
})

describe('formatPercent', () => {
  it('formats a number as percent with default 2 decimals', () => {
    expect(formatPercent(12.345)).toBe('12.35%')
  })

  it('returns "--" for null', () => {
    expect(formatPercent(null)).toBe('--')
  })

  it('respects custom digit count', () => {
    expect(formatPercent(5.1, 1)).toBe('5.1%')
  })
})

describe('formatSignedNumber', () => {
  it('prepends "+" for positive numbers', () => {
    expect(formatSignedNumber(42.1)).toBe('+42.10')
  })

  it('does not prepend anything for negative numbers', () => {
    expect(formatSignedNumber(-10.5)).toBe('-10.50')
  })

  it('returns "--" for null', () => {
    expect(formatSignedNumber(null)).toBe('--')
  })

  it('formats zero without sign prefix', () => {
    expect(formatSignedNumber(0)).toBe('0.00')
  })
})

describe('formatSignedPercent', () => {
  it('prepends "+" for positive percent', () => {
    expect(formatSignedPercent(5.25)).toBe('+5.25%')
  })

  it('returns "--" for undefined', () => {
    expect(formatSignedPercent(undefined)).toBe('--')
  })
})

describe('pnlClass', () => {
  it('returns positive class for positive value', () => {
    expect(pnlClass(100)).toBe('table-pnl--positive')
  })

  it('returns negative class for negative value', () => {
    expect(pnlClass(-50)).toBe('table-pnl--negative')
  })

  it('returns neutral class for zero', () => {
    expect(pnlClass(0)).toBe('table-pnl--neutral')
  })

  it('returns neutral class for null', () => {
    expect(pnlClass(null)).toBe('table-pnl--neutral')
  })

  it('returns neutral class for undefined', () => {
    expect(pnlClass(undefined)).toBe('table-pnl--neutral')
  })
})

describe('toneClass', () => {
  it('returns positive for positive value', () => {
    expect(toneClass(1)).toBe('positive')
  })

  it('returns negative for negative value', () => {
    expect(toneClass(-1)).toBe('negative')
  })

  it('returns neutral for zero', () => {
    expect(toneClass(0)).toBe('neutral')
  })

  it('returns neutral for null', () => {
    expect(toneClass(null)).toBe('neutral')
  })
})
