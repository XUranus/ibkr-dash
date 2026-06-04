import type { TradeItem } from '@/types/trades'
import { formatNumber, pnlClass } from '@/utils/format'

interface Props {
  items: TradeItem[]
  sortKey: 'proceeds' | 'fifo_pnl_realized' | null
  sortOrder: 'asc' | 'desc'
  onSort: (key: 'proceeds' | 'fifo_pnl_realized') => void
}

function formatSide(value: string | null): string {
  if (value === 'BUY') return 'Buy'
  if (value === 'SELL') return 'Sell'
  return value ?? '--'
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
  return (
    <div className="table-shell">
      <table className="data-table" style={{ minWidth: 1400 }}>
        <thead>
          <tr>
            <th style={{ width: '14%' }}>Date/Time</th>
            <th style={{ width: '23%' }}>Symbol</th>
            <th style={{ width: '8%', textAlign: 'center' }}>Asset</th>
            <th style={{ width: '6%', textAlign: 'center' }}>Side</th>
            <th style={{ width: '8%', textAlign: 'right' }}>Qty</th>
            <th style={{ width: '8%', textAlign: 'right' }}>Price</th>
            <th style={{ width: '11%', textAlign: 'right' }}>
              <button className="sort-button" onClick={() => onSort('proceeds')}>
                <span>Proceeds</span>
                <span className="sort-button__indicator">{sortIndicator(sortKey, sortOrder, 'proceeds')}</span>
              </button>
            </th>
            <th style={{ width: '7%', textAlign: 'right' }}>Commission</th>
            <th style={{ width: '9%', textAlign: 'right' }}>
              <button className="sort-button" onClick={() => onSort('fifo_pnl_realized')}>
                <span>Realized P&L</span>
                <span className="sort-button__indicator">{sortIndicator(sortKey, sortOrder, 'fifo_pnl_realized')}</span>
              </button>
            </th>
            <th style={{ width: '6%' }}>Exchange</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr><td colSpan={10} style={{ textAlign: 'center', padding: '2rem' }}>No trade data</td></tr>
          ) : items.map((item) => (
            <tr key={item.trade_id || item.transaction_id || `${item.date_time}-${item.symbol}`}>
              <td style={{ whiteSpace: 'normal' }}>
                <div className="table-symbol">
                  <span className="table-symbol__code">{item.date_time ?? '--'}</span>
                  <span className="table-symbol__desc">{item.trade_date ?? '--'}</span>
                </div>
              </td>
              <td style={{ whiteSpace: 'normal' }}>
                <div className="table-symbol">
                  <span className="table-symbol__code">{item.symbol ?? '--'}</span>
                  <span className="table-symbol__desc">{item.description ?? 'No name'}</span>
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
