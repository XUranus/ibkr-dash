import { useTranslation } from 'react-i18next'
import type { TradeItem } from '@/types/trades'
import { formatNumber, pnlClass } from '@/utils/format'

function extractDate(iso: string | null | undefined): string {
  if (!iso) return '--'
  return iso.split('T')[0]
}

function extractTime(iso: string | null | undefined): string {
  if (!iso) return '--'
  const parts = iso.split('T')
  if (parts.length < 2) return '--'
  // Handle "2026-06-12T11:33:46" or "2026-06-12;11:33:46"
  const time = parts[1].split(';')[0].split('.')[0]
  return time || '--'
}

interface Props {
  items: TradeItem[]
  sortKey: 'proceeds' | 'fifo_pnl_realized' | null
  sortOrder: 'asc' | 'desc'
  onSort: (key: 'proceeds' | 'fifo_pnl_realized') => void
}

function sideTagClass(value: string | null): string {
  if (value === 'BUY') return 'tag--positive'
  if (value === 'SELL') return 'tag--negative'
  return 'tag--accent'
}

function sortIndicator(activeKey: string | null, activeOrder: string, key: string): string {
  if (activeKey !== key) return '↕'
  return activeOrder === 'desc' ? '↓' : '↑'
}

export default function TradeTable({ items, sortKey, sortOrder, onSort }: Props) {
  const { t } = useTranslation()

  function formatSide(value: string | null): string {
    if (value === 'BUY') return t('trades.buy')
    if (value === 'SELL') return t('trades.sell')
    return value ?? '--'
  }

  return (
    <div className="table-shell">
      <table className="data-table" style={{ minWidth: 1400 }}>
        <thead>
          <tr>
            <th style={{ width: '14%' }}>{t('trades.dateTime')}</th>
            <th style={{ width: '23%' }}>{t('trades.symbol')}</th>
            <th style={{ width: '8%', textAlign: 'center' }}>{t('trades.asset')}</th>
            <th style={{ width: '6%', textAlign: 'center' }}>{t('trades.side')}</th>
            <th style={{ width: '8%', textAlign: 'right' }}>{t('trades.quantity')}</th>
            <th style={{ width: '8%', textAlign: 'right' }}>{t('trades.price')}</th>
            <th style={{ width: '11%', textAlign: 'right' }}>
              <button className="sort-button" onClick={() => onSort('proceeds')}>
                <span>{t('trades.proceeds')}</span>
                <span className="sort-button__indicator">{sortIndicator(sortKey, sortOrder, 'proceeds')}</span>
              </button>
            </th>
            <th style={{ width: '7%', textAlign: 'right' }}>{t('trades.commission')}</th>
            <th style={{ width: '9%', textAlign: 'right' }}>
              <button className="sort-button" onClick={() => onSort('fifo_pnl_realized')}>
                <span>{t('trades.realizedPnl')}</span>
                <span className="sort-button__indicator">{sortIndicator(sortKey, sortOrder, 'fifo_pnl_realized')}</span>
              </button>
            </th>
            <th style={{ width: '6%' }}>{t('trades.exchange')}</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr><td colSpan={10} style={{ textAlign: 'center', padding: '2rem' }}>{t('trades.noTradeData')}</td></tr>
          ) : items.map((item, index) => (
            <tr key={item.trade_id || item.transaction_id || `${item.date_time}-${item.symbol}-${index}`}>
              <td style={{ whiteSpace: 'normal' }}>
                <div className="table-symbol">
                  <span className="table-symbol__code">{extractDate(item.date_time) || item.trade_date || '--'}</span>
                  <span className="table-symbol__desc">{extractTime(item.date_time)}</span>
                </div>
              </td>
              <td style={{ whiteSpace: 'normal' }}>
                <div className="table-symbol">
                  <span className="table-symbol__code">{item.symbol ?? '--'}</span>
                  <span className="table-symbol__desc">{item.description ?? t('positions.noName')}</span>
                </div>
              </td>
              <td style={{ textAlign: 'center' }}><span className={`tag tag--accent`}>{item.asset_class ?? '--'}</span></td>
              <td style={{ textAlign: 'center' }}><span className={`tag ${sideTagClass(item.buy_sell)}`}>{formatSide(item.buy_sell)}</span></td>
              <td className="table-number"><span className="cell-number">{formatNumber(item.quantity, 4)}</span></td>
              <td className="table-number"><span className="cell-number">{formatNumber(item.trade_price, 2)}</span></td>
              <td className="table-number"><span className="cell-number">{formatNumber(item.proceeds, 2)}</span></td>
              <td className="table-number"><span className={`cell-number ${pnlClass(item.ib_commission)}`}>{formatNumber(item.ib_commission, 4)}</span></td>
              <td className="table-number"><span className={`cell-number ${pnlClass(item.fifo_pnl_realized)}`}>{formatNumber(item.fifo_pnl_realized, 2)}</span></td>
              <td><span className="terminal-muted">{item.exchange ?? '--'}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
