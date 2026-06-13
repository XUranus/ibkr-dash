import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchTradeSummary, fetchTrades } from '@/api/trades'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import StatCard from '@/components/StatCard'
import TradeTable from '@/components/TradeTable'
import type { TradeItem, TradeListResponse, TradeSummaryResponse } from '@/types/trades'
import { formatNumber } from '@/utils/format'

export default function TradesView() {
  const { t } = useTranslation()
  const [state, setState] = useState({ start_date: '', end_date: '', symbol: '', buy_sell: '', page: 1, page_size: 20 })
  const [tradeResponse, setTradeResponse] = useState<TradeListResponse | null>(null)
  const [tradeSummary, setTradeSummary] = useState<TradeSummaryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [sortKey, setSortKey] = useState<'proceeds' | 'fifo_pnl_realized' | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const currentSortBy = sortKey ?? 'date_time'

  async function loadTrades() {
    setLoading(true)
    setErrorMessage('')
    try {
      const filters = { start_date: state.start_date, end_date: state.end_date, symbol: state.symbol.trim().toUpperCase(), buy_sell: state.buy_sell }
      const [summaryResponse, listResponse] = await Promise.all([
        fetchTradeSummary(filters),
        fetchTrades({ ...filters, sort_by: currentSortBy, sort_order: sortOrder, page: state.page, page_size: state.page_size }),
      ])
      setTradeSummary(summaryResponse)
      setTradeResponse(listResponse)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('trades.failedToLoadTrades'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void loadTrades() }, [])

  function applyFilters() {
    setState((s) => ({ ...s, page: 1 }))
    void loadTrades()
  }

  function setSort(key: 'proceeds' | 'fifo_pnl_realized') {
    if (sortKey === key) setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
    else { setSortKey(key); setSortOrder('desc') }
    setState((s) => ({ ...s, page: 1 }))
  }

  function onPageChange(newPage: number) {
    setState((s) => ({ ...s, page: newPage }))
  }

  useEffect(() => { void loadTrades() }, [state.page])

  const tradeItems = tradeResponse?.items ?? []
  const pagination = tradeResponse?.pagination
  const totalPages = pagination?.total_pages ?? 1

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <h2 className="panel-title">{t('trades.tradeFilters')}</h2>
              <p className="panel-subtitle">{t('trades.tradeFiltersDesc')}</p>
            </div>
          </div>
          <form style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 'var(--space-3)', alignItems: 'end' }} onSubmit={(e) => { e.preventDefault(); applyFilters() }}>
            <label className="field-stack">
              <span className="field-stack__label">{t('trades.startDate')}</span>
              <input className="input" type="date" value={state.start_date} onChange={(e) => setState({ ...state, start_date: e.target.value })} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('trades.endDate')}</span>
              <input className="input" type="date" value={state.end_date} onChange={(e) => setState({ ...state, end_date: e.target.value })} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('trades.symbol')}</span>
              <input className="input" type="text" placeholder="AAPL" value={state.symbol} onChange={(e) => setState({ ...state, symbol: e.target.value })} />
            </label>
            <div className="field-stack">
              <span className="field-stack__label">{t('trades.direction')}</span>
              <div style={{ display: 'flex', gap: 10 }}>
                <button type="button" className={`btn ${state.buy_sell === 'BUY' ? 'btn--accent' : ''}`} onClick={() => setState({ ...state, buy_sell: state.buy_sell === 'BUY' ? '' : 'BUY' })}>{t('trades.buy')}</button>
                <button type="button" className={`btn ${state.buy_sell === 'SELL' ? 'btn--accent' : ''}`} onClick={() => setState({ ...state, buy_sell: state.buy_sell === 'SELL' ? '' : 'SELL' })}>{t('trades.sell')}</button>
              </div>
            </div>
            <div className="field-stack">
              <button type="submit" className="btn btn--accent" style={{ width: '100%' }}>{t('trades.search')}</button>
            </div>
          </form>
        </div>
      </section>

      {loading ? <LoadingBlock /> : errorMessage ? <ErrorBlock message={errorMessage} /> : (
        <>
          <section className="stats-grid stats-grid--summary">
            <StatCard title={t('trades.totalTrades')} value={String(tradeSummary?.trade_count ?? 0)} tone="accent" />
            <StatCard title={t('trades.buyCount')} value={String(tradeSummary?.buy_count ?? 0)} tone="positive" />
            <StatCard title={t('trades.sellCount')} value={String(tradeSummary?.sell_count ?? 0)} tone="negative" />
            <StatCard title={t('trades.symbols')} value={String(tradeSummary?.symbols_count ?? 0)} tone="neutral" />
            <StatCard title={t('trades.totalCommission')} value={formatNumber(tradeSummary?.total_commission ?? null, 2)} tone={(tradeSummary?.total_commission ?? 0) < 0 ? 'negative' : 'neutral'} />
            <StatCard title={t('trades.realizedPnl')} value={formatNumber(tradeSummary?.total_realized_pnl ?? null)} tone={(tradeSummary?.total_realized_pnl ?? 0) >= 0 ? 'positive' : 'negative'} />
          </section>

          <section className="surface-panel">
            <div className="surface-panel__content">
              <div className="section-header">
                <div>
                  <h2 className="panel-title">{t('trades.tradeDetails')}</h2>
                  <p className="panel-subtitle">{t('trades.tradeDetailsDesc')}</p>
                </div>
              </div>
              {tradeItems.length > 0 ? (
                <>
                  <TradeTable items={tradeItems} sortKey={sortKey} sortOrder={sortOrder} onSort={setSort} />
                  <div className="pager">
                    <span className="terminal-note">
                      {t('trades.pageInfo', { page: state.page, totalPages, total: pagination?.total ?? 0 })}
                    </span>
                    <div className="pager__pages">
                      <button className="pager__page" disabled={state.page <= 1} onClick={() => onPageChange(state.page - 1)}>{t('trades.prev')}</button>
                      {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1).map((p) => (
                        <button key={p} className={`pager__page ${p === state.page ? 'pager__page--active' : ''}`} onClick={() => onPageChange(p)}>{p}</button>
                      ))}
                      <button className="pager__page" disabled={state.page >= totalPages} onClick={() => onPageChange(state.page + 1)}>{t('trades.next')}</button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="empty-state">{t('trades.noTradeData')}</div>
              )}
            </div>
          </section>
        </>
      )}
    </section>
  )
}
