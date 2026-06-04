import { useState, useEffect, useCallback } from 'react'
import { fetchTradeSummary, fetchTrades } from '@/api/trades'
import ErrorBlock from '@/components/ErrorBlock'
import LoadingBlock from '@/components/LoadingBlock'
import StatCard from '@/components/StatCard'
import TradeTable from '@/components/TradeTable'
import type { TradeItem, TradeListResponse, TradeSummaryResponse } from '@/types/trades'
import { formatNumber } from '@/utils/format'

export default function TradesView() {
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
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load trades')
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
              <h2 className="panel-title">Trade Filters</h2>
              <p className="panel-subtitle">Filter by date, symbol, and direction. Sort via column headers.</p>
            </div>
          </div>
          <form style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 'var(--space-3)', alignItems: 'end' }} onSubmit={(e) => { e.preventDefault(); applyFilters() }}>
            <label className="field-stack">
              <span className="field-stack__label">Start Date</span>
              <input className="input" type="date" value={state.start_date} onChange={(e) => setState({ ...state, start_date: e.target.value })} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">End Date</span>
              <input className="input" type="date" value={state.end_date} onChange={(e) => setState({ ...state, end_date: e.target.value })} />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">Symbol</span>
              <input className="input" type="text" placeholder="AAPL" value={state.symbol} onChange={(e) => setState({ ...state, symbol: e.target.value })} />
            </label>
            <div className="field-stack">
              <span className="field-stack__label">Direction</span>
              <div style={{ display: 'flex', gap: 10 }}>
                <button type="button" className={`btn ${state.buy_sell === 'BUY' ? 'btn--accent' : ''}`} onClick={() => setState({ ...state, buy_sell: state.buy_sell === 'BUY' ? '' : 'BUY' })}>Buy</button>
                <button type="button" className={`btn ${state.buy_sell === 'SELL' ? 'btn--accent' : ''}`} onClick={() => setState({ ...state, buy_sell: state.buy_sell === 'SELL' ? '' : 'SELL' })}>Sell</button>
              </div>
            </div>
            <div className="field-stack">
              <button type="submit" className="btn btn--accent" style={{ width: '100%' }}>Search</button>
            </div>
          </form>
        </div>
      </section>

      {loading ? <LoadingBlock /> : errorMessage ? <ErrorBlock message={errorMessage} /> : (
        <>
          <section className="stats-grid stats-grid--summary">
            <StatCard title="Total Trades" value={String(tradeSummary?.trade_count ?? 0)} tone="accent" />
            <StatCard title="Buy Count" value={String(tradeSummary?.buy_count ?? 0)} tone="positive" />
            <StatCard title="Sell Count" value={String(tradeSummary?.sell_count ?? 0)} tone="negative" />
            <StatCard title="Symbols" value={String(tradeSummary?.symbols_count ?? 0)} tone="neutral" />
            <StatCard title="Total Commission" value={formatNumber(tradeSummary?.total_commission ?? null, 4)} tone={(tradeSummary?.total_commission ?? 0) < 0 ? 'negative' : 'neutral'} />
            <StatCard title="Realized P&L" value={formatNumber(tradeSummary?.total_realized_pnl ?? null)} tone={(tradeSummary?.total_realized_pnl ?? 0) >= 0 ? 'positive' : 'negative'} />
            <StatCard title="Net Proceeds" value={formatNumber(tradeSummary?.total_proceeds ?? null)} tone={(tradeSummary?.total_proceeds ?? 0) >= 0 ? 'positive' : 'negative'} />
          </section>

          <section className="surface-panel">
            <div className="surface-panel__content">
              <div className="section-header">
                <div>
                  <h2 className="panel-title">Trade Details</h2>
                  <p className="panel-subtitle">Click column headers to sort.</p>
                </div>
              </div>
              {tradeItems.length > 0 ? (
                <>
                  <TradeTable items={tradeItems} sortKey={sortKey} sortOrder={sortOrder} onSort={setSort} />
                  <div className="pager">
                    <span className="terminal-note">
                      Page {state.page} of {totalPages} ({pagination?.total ?? 0} total)
                    </span>
                    <div className="pager__pages">
                      <button className="pager__page" disabled={state.page <= 1} onClick={() => onPageChange(state.page - 1)}>Prev</button>
                      {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => i + 1).map((p) => (
                        <button key={p} className={`pager__page ${p === state.page ? 'pager__page--active' : ''}`} onClick={() => onPageChange(p)}>{p}</button>
                      ))}
                      <button className="pager__page" disabled={state.page >= totalPages} onClick={() => onPageChange(state.page + 1)}>Next</button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="empty-state">No trade data</div>
              )}
            </div>
          </section>
        </>
      )}
    </section>
  )
}
