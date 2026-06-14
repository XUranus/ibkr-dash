import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchDividendSummary, fetchDividends } from '@/api/dividends'
import DividendTable from '@/components/DividendTable'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import StatCard from '@/components/StatCard'
import type { DividendSummaryResponse } from '@/types/dividends'
import { formatNumber } from '@/utils/format'

export default function DividendsView() {
  const { t } = useTranslation()
  const [state, setState] = useState({ start_date: '', end_date: '', currency: '', symbol: '', page: 1, page_size: 20 })
  const [dividendResponse, setDividendResponse] = useState<Awaited<ReturnType<typeof fetchDividends>> | null>(null)
  const [dividendSummary, setDividendSummary] = useState<DividendSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [sortKey, setSortKey] = useState<'date_time' | 'ex_date' | 'amount' | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const currentSortBy = sortKey ?? 'date_time'

  async function loadDividends(includeSummary = true) {
    setLoading(true)
    setErrorMessage('')
    try {
      const filters = { start_date: state.start_date, end_date: state.end_date, currency: state.currency, symbol: state.symbol }
      // Load list first (critical)
      const listRes = await fetchDividends({ ...filters, sort_by: currentSortBy, sort_order: sortOrder, page: state.page, page_size: state.page_size })
      setDividendResponse(listRes)
      // Load summary independently (non-blocking)
      if (includeSummary) {
        fetchDividendSummary(filters)
          .then((res) => setDividendSummary(res))
          .catch(() => { /* summary failed, list still shows */ })
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('dividends.failedToLoadDividends'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadDividends() }, [])

  function applyFilters() { setState((s) => ({ ...s, page: 1 })); void loadDividends() }
  function setSort(key: 'date_time' | 'ex_date' | 'amount') {
    if (sortKey === key) setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortOrder('desc') }
    setState((s) => ({ ...s, page: 1 }))
  }
  function onPageChange(p: number) { setState((s) => ({ ...s, page: p })) }

  useEffect(() => { void loadDividends(false) }, [state.page])

  const items = dividendResponse?.items ?? []

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <h2 className="panel-title">{t('dividends.filters')}</h2>
              <p className="panel-subtitle">{t('dividends.filtersDesc')}</p>
            </div>
          </div>
          <form style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 'var(--space-3)', alignItems: 'end' }} onSubmit={(e) => { e.preventDefault(); applyFilters() }}>
            <label className="field-stack">
              <span className="field-stack__label">{t('dividends.startDate')}</span>
              <input className="input" type="date" value={state.start_date} onChange={(e) => setState({ ...state, start_date: e.target.value })} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('dividends.endDate')}</span>
              <input className="input" type="date" value={state.end_date} onChange={(e) => setState({ ...state, end_date: e.target.value })} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('dividends.currency')}</span>
              <input className="input" type="text" placeholder="USD / CNH / HKD" value={state.currency} onChange={(e) => setState({ ...state, currency: e.target.value })} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('dividends.symbol')}</span>
              <input className="input" type="text" placeholder="AAPL / MSFT / SGOV" value={state.symbol} onChange={(e) => setState({ ...state, symbol: e.target.value })} />
            </label>
            <div className="field-stack">
              <button type="submit" className="btn btn--accent" style={{ width: '100%' }}>{t('dividends.search')}</button>
            </div>
          </form>
        </div>
      </section>

      {loading ? <LoadingBlock /> : errorMessage ? <ErrorBlock message={errorMessage} /> : (
        <>
          <section className="stats-grid stats-grid--summary">
            <StatCard title={t('dividends.records')} value={String(dividendSummary?.record_count ?? 0)} tone="accent" />
            <StatCard title={t('dividends.grossDividends')} value={formatNumber(dividendSummary?.gross_dividend_amount ?? null)} tone="positive" />
            <StatCard title={t('dividends.withholdingTax')} value={formatNumber(dividendSummary?.withholding_tax_amount ?? null)} tone="negative" />
            <StatCard title={t('dividends.netReceived')} value={formatNumber(dividendSummary?.net_amount ?? null)} tone={(dividendSummary?.net_amount ?? 0) >= 0 ? 'positive' : 'negative'} />
          </section>

          <section className="surface-panel">
            <div className="surface-panel__content">
              <div className="section-header">
                <div>
                  <h2 className="panel-title">{t('dividends.dividendDetails')}</h2>
                  <p className="panel-subtitle">{t('dividends.dividendDetailsDesc')}</p>
                </div>
              </div>
              {items.length > 0 ? (
                <>
                  <DividendTable items={items} sortKey={sortKey} sortOrder={sortOrder} onSort={setSort} />
                  <div className="pager">
                    <span className="terminal-note">{t('dividends.pageInfo', { page: state.page, totalPages: dividendResponse?.pagination?.total_pages ?? 1 })}</span>
                    <div className="pager__pages">
                      <button className="pager__page" disabled={state.page <= 1} onClick={() => onPageChange(state.page - 1)}>{t('dividends.prev')}</button>
                      <button className="pager__page" disabled={state.page >= (dividendResponse?.pagination?.total_pages ?? 1)} onClick={() => onPageChange(state.page + 1)}>{t('dividends.next')}</button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="empty-state">{t('dividends.noDividendRecords')}</div>
              )}
            </div>
          </section>
        </>
      )}
    </section>
  )
}
