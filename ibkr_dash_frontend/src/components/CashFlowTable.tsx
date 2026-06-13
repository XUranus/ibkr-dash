import { useTranslation } from 'react-i18next'
import type { CashFlowItem } from '@/types/cashFlows'
import { formatNumber, pnlClass } from '@/utils/format'

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '--'
  const datePart = iso.split('T')[0]
  const [y, m, d] = datePart.split('-')
  if (!y || !m || !d) return iso
  return `${y}-${m}-${d}`
}

interface Props {
  items: CashFlowItem[]
  sortKey: 'date_time' | 'amount' | null
  sortOrder: 'asc' | 'desc'
  onSort: (key: 'date_time' | 'amount') => void
}

function directionLabel(value: string | null, t: (key: string) => string): string {
  if (value === 'deposit') return t('cashFlows.deposit')
  if (value === 'withdrawal') return t('cashFlows.withdrawal')
  return value ?? '--'
}

function directionTagClass(value: string | null): string {
  if (value === 'deposit') return 'tag--positive'
  if (value === 'withdrawal') return 'tag--negative'
  return 'tag--accent'
}

function sortIndicator(activeKey: string | null, activeOrder: string, key: string): string {
  if (activeKey !== key) return '↕'
  return activeOrder === 'desc' ? '↓' : '↑'
}

export default function CashFlowTable({ items, sortKey, sortOrder, onSort }: Props) {
  const { t } = useTranslation()
  return (
    <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: '17%' }}>
              <button className="sort-button" style={{ justifyContent: 'flex-start' }} onClick={() => onSort('date_time')}>
                <span>{t('cashFlows.dateTime')}</span>
                <span className="sort-button__indicator">{sortIndicator(sortKey, sortOrder, 'date_time')}</span>
              </button>
            </th>
            <th style={{ width: '9%', textAlign: 'center' }}>{t('cashFlows.currency')}</th>
            <th style={{ width: '7%', textAlign: 'center' }}>{t('cashFlows.direction')}</th>
            <th style={{ width: '12%', textAlign: 'right' }}>
              <button className="sort-button" onClick={() => onSort('amount')}>
                <span>{t('cashFlows.amount')}</span>
                <span className="sort-button__indicator">{sortIndicator(sortKey, sortOrder, 'amount')}</span>
              </button>
            </th>
            <th style={{ width: '10%' }}>{t('cashFlows.settleDate')}</th>
            <th style={{ width: '27%' }}>{t('cashFlows.description')}</th>
            <th style={{ width: '18%' }}>{t('cashFlows.transactionId')}</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr><td colSpan={7} style={{ textAlign: 'center', padding: '2rem' }}>{t('cashFlows.noCashFlowRecords')}</td></tr>
          ) : items.map((item) => (
            <tr key={item.transaction_id || `${item.date_time}-${item.amount}`}>
              <td style={{ whiteSpace: 'normal' }}>
                <div className="table-symbol">
                  <span className="table-symbol__code">{formatDate(item.settle_date || item.date_time)}</span>
                </div>
              </td>
              <td style={{ textAlign: 'center' }}><span className="tag tag--accent">{item.currency ?? '--'}</span></td>
              <td style={{ textAlign: 'center' }}><span className={`tag ${directionTagClass(item.flow_direction)}`}>{directionLabel(item.flow_direction, t)}</span></td>
              <td className="table-number"><span className={`cell-number ${pnlClass(item.amount)}`}>{formatNumber(item.amount, 2)}</span></td>
              <td><span className="terminal-muted">{formatDate(item.settle_date)}</span></td>
              <td>
                <div className="table-symbol">
                  <span className="table-symbol__code">{item.description ?? '--'}</span>
                  <span className="table-symbol__desc">{item.client_reference ?? item.flow_type ?? '--'}</span>
                </div>
              </td>
              <td><span className="terminal-muted">{item.transaction_id ?? '--'}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
