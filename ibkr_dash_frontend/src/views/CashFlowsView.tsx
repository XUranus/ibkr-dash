import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchCashFlows, fetchCashFlowSummary } from '@/api/cashFlows'
import CashFlowTable from '@/components/CashFlowTable'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import StatCard from '@/components/StatCard'
import type { CashFlowSummaryResponse } from '@/types/cashFlows'
import { formatNumber } from '@/utils/format'

export default function CashFlowsView() {
  const { t } = useTranslation()
  const [state, setState] = useState({ start_date: '', end_date: '', currency: '', flow_direction: '', page: 1, page_size: 20 })
  const [cashFlowResponse, setCashFlowResponse] = useState<Awaited<ReturnType<typeof fetchCashFlows>> | null>(null)
  const [cashFlowSummary, setCashFlowSummary] = useState<CashFlowSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [sortKey, setSortKey] = useState<'date_time' | 'amount' | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const currentSortBy = sortKey ?? 'date_time'

  async function loadCashFlows(includeSummary = true) {
    setLoading(true)
    setErrorMessage('')
    try {
      const filters = { start_date: state.start_date, end_date: state.end_date, currency: state.currency, flow_direction: state.flow_direction }
      // Load list first (critical)
      const listResponse = await fetchCashFlows({ ...filters, sort_by: currentSortBy, sort_order: sortOrder, page: state.page, page_size: state.page_size })
      setCashFlowResponse(listResponse)
      // Load summary independently (non-blocking)
      if (includeSummary) {
        fetchCashFlowSummary(filters)
          .then((res) => setCashFlowSummary(res))
          .catch(() => { /* summary failed, list still shows */ })
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('cashFlows.failedToLoadCashFlows'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadCashFlows() }, [])

  function applyFilters() { setState((s) => ({ ...s, page: 1 })); void loadCashFlows() }
  function setDirection(dir: 'deposit' | 'withdrawal') { setState((s) => ({ ...s, flow_direction: s.flow_direction === dir ? '' : dir, page: 1 })); void loadCashFlows() }
  function setSort(key: 'date_time' | 'amount') {
    if (sortKey === key) setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortOrder('desc') }
    setState((s) => ({ ...s, page: 1 }))
  }
  function onPageChange(p: number) { setState((s) => ({ ...s, page: p })) }

  useEffect(() => { void loadCashFlows(false) }, [state.page])

  const items = cashFlowResponse?.items ?? []
  const totalPages = cashFlowResponse?.pagination?.total_pages ?? 1

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <h2 className="panel-title">{t('cashFlows.filters')}</h2>
              <p className="panel-subtitle">{t('cashFlows.filtersDesc')}</p>
            </div>
          </div>
          <form style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 'var(--space-3)', alignItems: 'end' }} onSubmit={(e) => { e.preventDefault(); applyFilters() }}>
            <label className="field-stack">
              <span className="field-stack__label">{t('cashFlows.startDate')}</span>
              <input className="input" type="date" value={state.start_date} onChange={(e) => setState({ ...state, start_date: e.target.value })} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('cashFlows.endDate')}</span>
              <input className="input" type="date" value={state.end_date} onChange={(e) => setState({ ...state, end_date: e.target.value })} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('cashFlows.currency')}</span>
              <input className="input" type="text" placeholder="USD / CNH / HKD" value={state.currency} onChange={(e) => setState({ ...state, currency: e.target.value })} />
            </label>
            <div className="field-stack">
              <span className="field-stack__label">{t('cashFlows.direction')}</span>
              <div style={{ display: 'flex', gap: 10 }}>
                <button type="button" className={`btn ${state.flow_direction === 'deposit' ? 'btn--accent' : ''}`} onClick={() => setDirection('deposit')}>{t('cashFlows.deposit')}</button>
                <button type="button" className={`btn ${state.flow_direction === 'withdrawal' ? 'btn--accent' : ''}`} onClick={() => setDirection('withdrawal')}>{t('cashFlows.withdrawal')}</button>
              </div>
            </div>
            <div className="field-stack">
              <button type="submit" className="btn btn--accent" style={{ width: '100%' }}>{t('cashFlows.search')}</button>
            </div>
          </form>
        </div>
      </section>

      {loading ? <LoadingBlock /> : errorMessage ? <ErrorBlock message={errorMessage} /> : (
        <>
          <section className="stats-grid stats-grid--summary">
            <StatCard title={t('cashFlows.records')} value={String(cashFlowSummary?.record_count ?? 0)} tone="accent" />
            <StatCard title={t('cashFlows.deposits')} value={String(cashFlowSummary?.deposit_count ?? 0)} tone="positive" />
            <StatCard title={t('cashFlows.withdrawals')} value={String(cashFlowSummary?.withdrawal_count ?? 0)} tone="negative" />
          </section>

          {cashFlowSummary?.by_currency && cashFlowSummary.by_currency.length > 0 && (
            <div style={{ display: 'grid', gap: 'var(--space-4)' }}>
              {cashFlowSummary.by_currency.map((item) => (
                <section key={item.currency ?? 'unknown'} className="surface-panel">
                  <div className="surface-panel__content">
                    <div className="section-header">
                      <div>
                        <h2 className="panel-title">{item.currency ?? 'Unknown'} {t('cashFlows.summary')}</h2>
                        <p className="panel-subtitle">{t('cashFlows.summaryDesc', { count: item.record_count, deposits: item.deposit_count, withdrawals: item.withdrawal_count })}</p>
                      </div>
                    </div>
                    <section className="stats-grid stats-grid--summary">
                      <StatCard title={t('cashFlows.totalDeposits')} value={formatNumber(item.total_deposit_amount)} tone="positive" />
                      <StatCard title={t('cashFlows.totalWithdrawals')} value={formatNumber(item.total_withdrawal_amount)} tone="negative" />
                      <StatCard title={t('cashFlows.netFlow')} value={formatNumber(item.net_amount)} tone={item.net_amount >= 0 ? 'positive' : 'negative'} />
                    </section>
                  </div>
                </section>
              ))}
            </div>
          )}

          <section className="surface-panel">
            <div className="surface-panel__content">
              <div className="section-header">
                <div>
                  <h2 className="panel-title">{t('cashFlows.cashFlowDetails')}</h2>
                  <p className="panel-subtitle">{t('cashFlows.cashFlowDetailsDesc')}</p>
                </div>
              </div>
              {items.length > 0 ? (
                <>
                  <CashFlowTable items={items} sortKey={sortKey} sortOrder={sortOrder} onSort={setSort} />
                  <div className="pager">
                    <span className="terminal-note">{t('cashFlows.pageInfo', { page: state.page, totalPages, total: cashFlowResponse?.pagination?.total ?? 0 })}</span>
                    <div className="pager__pages">
                      <button className="pager__page" disabled={state.page <= 1} onClick={() => onPageChange(state.page - 1)}>{t('cashFlows.prev')}</button>
                      <button className="pager__page" disabled={state.page >= totalPages} onClick={() => onPageChange(state.page + 1)}>{t('cashFlows.next')}</button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="empty-state">{t('cashFlows.noCashFlowRecords')}</div>
              )}
            </div>
          </section>
        </>
      )}
    </section>
  )
}
