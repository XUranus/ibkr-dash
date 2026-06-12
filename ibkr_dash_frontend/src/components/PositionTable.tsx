import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { PositionItem } from '@/types/positions'
import { formatNumber, formatSignedPercent, pnlClass } from '@/utils/format'

interface Props {
  items: PositionItem[]
  onSelect: (item: PositionItem) => void
}

type SortKey = 'previous_day_change_percent' | 'total_realized_pnl' | 'total_unrealized_pnl' | 'cost_basis_money' | 'position_value' | 'percent_of_nav'

export default function PositionTable({ items, onSelect }: Props) {
  const { t } = useTranslation()

  const sortableLabels: Record<SortKey, string> = {
    previous_day_change_percent: t('positions.dailyChg'),
    total_realized_pnl: t('positions.realizedPnl'),
    total_unrealized_pnl: t('positions.unrealizedPnl'),
    cost_basis_money: t('positions.cost'),
    position_value: t('positions.marketValue'),
    percent_of_nav: t('positions.percentNav'),
  }
  const [sortKey, setSortKey] = useState<SortKey>('position_value')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const sortedItems = useMemo(() => {
    const values = [...items]
    values.sort((a, b) => {
      const leftVal = typeof a[sortKey] === 'number' ? (a[sortKey] as number) : Number.NEGATIVE_INFINITY
      const rightVal = typeof b[sortKey] === 'number' ? (b[sortKey] as number) : Number.NEGATIVE_INFINITY
      const result = leftVal - rightVal
      return sortOrder === 'asc' ? result : -result
    })
    return values
  }, [items, sortKey, sortOrder])

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    } else {
      setSortKey(key)
      setSortOrder('desc')
    }
  }

  function sortIndicator(key: SortKey): string {
    if (sortKey !== key) return '↕'
    return sortOrder === 'desc' ? '↓' : '↑'
  }

  function percentText(value: number | null): string {
    if (value === null) return '--'
    return `${formatNumber(value, 2)}%`
  }

  return (
    <>
      <div className="table-shell" style={{ display: 'block' }}>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '23%' }}>{t('positions.symbol')}</th>
              <th style={{ width: '7%', textAlign: 'right' }}>{t('positions.quantity')}</th>
              <th style={{ width: '7.5%', textAlign: 'right' }}>{t('positions.avgCost')}</th>
              <th style={{ width: '7%', textAlign: 'right' }}>
                <button className="sort-button" onClick={() => handleSort('previous_day_change_percent')}>
                  <span>{sortableLabels.previous_day_change_percent}</span>
                  <span className="sort-button__indicator">{sortIndicator('previous_day_change_percent')}</span>
                </button>
              </th>
              <th style={{ width: '10%', textAlign: 'right' }}>
                <button className="sort-button" onClick={() => handleSort('total_unrealized_pnl')}>
                  <span>{sortableLabels.total_unrealized_pnl}</span>
                  <span className="sort-button__indicator">{sortIndicator('total_unrealized_pnl')}</span>
                </button>
              </th>
              <th style={{ width: '10%', textAlign: 'right' }}>
                <button className="sort-button" onClick={() => handleSort('total_realized_pnl')}>
                  <span>{sortableLabels.total_realized_pnl}</span>
                  <span className="sort-button__indicator">{sortIndicator('total_realized_pnl')}</span>
                </button>
              </th>
              <th style={{ width: '9%', textAlign: 'right' }}>
                <button className="sort-button" onClick={() => handleSort('cost_basis_money')}>
                  <span>{sortableLabels.cost_basis_money}</span>
                  <span className="sort-button__indicator">{sortIndicator('cost_basis_money')}</span>
                </button>
              </th>
              <th style={{ width: '7.5%', textAlign: 'right' }}>{t('positions.markPrice')}</th>
              <th style={{ width: '10%', textAlign: 'right' }}>
                <button className="sort-button" onClick={() => handleSort('position_value')}>
                  <span>{sortableLabels.position_value}</span>
                  <span className="sort-button__indicator">{sortIndicator('position_value')}</span>
                </button>
              </th>
              <th style={{ width: '8%', textAlign: 'right' }}>
                <button className="sort-button" onClick={() => handleSort('percent_of_nav')}>
                  <span>{sortableLabels.percent_of_nav}</span>
                  <span className="sort-button__indicator">{sortIndicator('percent_of_nav')}</span>
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedItems.length === 0 ? (
              <tr><td colSpan={10} style={{ textAlign: 'center', padding: '2rem' }}>{t('positions.noData')}</td></tr>
            ) : sortedItems.map((item) => (
              <tr key={`${item.account_id}-${item.symbol}-${item.asset_class}`} style={{ cursor: 'pointer' }} onClick={() => onSelect(item)}>
                <td style={{ whiteSpace: 'normal' }}>
                  <div className="table-symbol">
                    <span className="table-symbol__code">{item.symbol ?? '--'}</span>
                    <span className="table-symbol__desc">{item.description ?? t('positions.noName')}</span>
                  </div>
                </td>
                <td className="table-number"><span className="cell-number">{formatNumber(item.quantity, 0)}</span></td>
                <td className="table-number"><span className="cell-number">{formatNumber(item.average_cost_price, 2)}</span></td>
                <td className="table-number">
                  <span className={`cell-number ${pnlClass(item.previous_day_change_percent)}`}>
                    {formatSignedPercent(item.previous_day_change_percent)}
                  </span>
                </td>
                <td className="table-number">
                  <div style={{ display: 'grid', justifyItems: 'end', gap: 2 }}>
                    <span className={`cell-number ${pnlClass(item.total_unrealized_pnl)}`}>{formatNumber(item.total_unrealized_pnl, 2)}</span>
                    <span style={{ fontSize: '0.82rem', opacity: 0.82 }} className={pnlClass(item.unrealized_pnl_percent)}>{formatSignedPercent(item.unrealized_pnl_percent)}</span>
                  </div>
                </td>
                <td className="table-number">
                  <div style={{ display: 'grid', justifyItems: 'end', gap: 2 }}>
                    <span className={`cell-number ${pnlClass(item.total_realized_pnl)}`}>{formatNumber(item.total_realized_pnl, 2)}</span>
                    <span style={{ fontSize: '0.82rem', opacity: 0.82 }} className={pnlClass(item.realized_pnl_percent)}>{formatSignedPercent(item.realized_pnl_percent)}</span>
                  </div>
                </td>
                <td className="table-number"><span className="cell-number">{formatNumber(item.cost_basis_money, 2)}</span></td>
                <td className="table-number"><span className="cell-number">{formatNumber(item.mark_price, 2)}</span></td>
                <td className="table-number"><span className="cell-number">{formatNumber(item.position_value, 2)}</span></td>
                <td className="table-number"><span className="cell-number">{percentText(item.percent_of_nav)}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
