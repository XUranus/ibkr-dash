import { useTranslation } from 'react-i18next'
import type { DividendItem } from '@/types/dividends'
import { formatNumber, pnlClass } from '@/utils/format'

interface Props {
  items: DividendItem[]
  sortKey: 'date_time' | 'ex_date' | 'amount' | null
  sortOrder: 'asc' | 'desc'
  onSort: (key: 'date_time' | 'ex_date' | 'amount') => void
}

function flowTypeLabel(value: string | null): string {
  if (value === 'Dividends' || value === 'Ordinary Dividend') return 'Dividend'
  if (value === 'Withholding Tax') return 'WHT'
  if (value?.includes('Payment In Lieu')) return 'PIL'
  return value ?? '--'
}

function flowTypeTagClass(value: string | null): string {
  if (value === 'Withholding Tax') return 'tag--negative'
  if (value?.includes('Payment In Lieu')) return 'tag--accent'
  if (value?.includes('Dividend')) return 'tag--positive'
  return 'tag--accent'
}

function sortIndicator(activeKey: string | null, activeOrder: string, key: string): string {
  if (activeKey !== key) return '↕'
  return activeOrder === 'desc' ? '↓' : '↑'
}

export default function DividendTable({ items, sortKey, sortOrder, onSort }: Props) {
  const { t } = useTranslation()

  return (
    <div className="table-shell">
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: '17%' }}>
              <button className="sort-button" style={{ justifyContent: 'flex-start' }} onClick={() => onSort('date_time')}>
                <span>{t('dividends.settlementDate')}</span>
                <span className="sort-button__indicator">{sortIndicator(sortKey, sortOrder, 'date_time')}</span>
              </button>
            </th>
            <th style={{ width: '10%' }}>
              <button className="sort-button" style={{ justifyContent: 'flex-start' }} onClick={() => onSort('ex_date')}>
                <span>{t('dividends.exDate')}</span>
                <span className="sort-button__indicator">{sortIndicator(sortKey, sortOrder, 'ex_date')}</span>
              </button>
            </th>
            <th style={{ width: '20%' }}>{t('dividends.symbol')}</th>
            <th style={{ width: '9%', textAlign: 'center' }}>{t('dividends.type')}</th>
            <th style={{ width: '7%', textAlign: 'center' }}>{t('dividends.currency')}</th>
            <th style={{ width: '12%', textAlign: 'right' }}>
              <button className="sort-button" onClick={() => onSort('amount')}>
                <span>{t('dividends.amount')}</span>
                <span className="sort-button__indicator">{sortIndicator(sortKey, sortOrder, 'amount')}</span>
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr><td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>{t('dividends.noDividendRecords')}</td></tr>
          ) : items.map((item) => (
            <tr key={item.transaction_id || `${item.date_time}-${item.symbol}-${item.amount}`}>
              <td style={{ whiteSpace: 'normal' }}>
                <div className="table-symbol">
                  <span className="table-symbol__code">{item.date_time ?? '--'}</span>
                  <span className="table-symbol__desc">{item.settle_date ?? item.report_date ?? '--'}</span>
                </div>
              </td>
              <td><span className="terminal-muted">{item.ex_date ?? '--'}</span></td>
              <td>
                <div className="table-symbol">
                  <span className="table-symbol__code">{item.symbol ?? '--'}</span>
                  <span className="table-symbol__desc">{item.description ?? '--'}</span>
                </div>
              </td>
              <td style={{ textAlign: 'center' }}><span className={`tag ${flowTypeTagClass(item.flow_type)}`}>{flowTypeLabel(item.flow_type)}</span></td>
              <td style={{ textAlign: 'center' }}><span className="tag tag--accent">{item.currency ?? '--'}</span></td>
              <td className="table-number"><span className={`cell-number ${pnlClass(item.amount)}`}>{formatNumber(item.amount, 2)}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
