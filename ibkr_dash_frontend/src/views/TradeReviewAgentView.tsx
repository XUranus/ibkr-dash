import { useState, useEffect, useCallback } from 'react'
import { fetchRecentTradeReviews, fetchTradeReviewDetail, fetchTradeReviewHealth, startSingleTradeReviewTask, startSymbolReviewTask } from '@/api/tradeReview'
import type { TradeReviewHealth, TradeReviewResult } from '@/types/tradeReview'

export default function TradeReviewAgentView() {
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [health, setHealth] = useState<TradeReviewHealth | null>(null)
  const [reviews, setReviews] = useState<TradeReviewResult[]>([])
  const [selectedReview, setSelectedReview] = useState<TradeReviewResult | null>(null)
  const [symbol, setSymbol] = useState('')
  const [tradeId, setTradeId] = useState('')
  const [generating, setGenerating] = useState(false)
  const [activeTab, setActiveTab] = useState<'symbol' | 'single'>('symbol')

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const [h, r] = await Promise.all([fetchTradeReviewHealth(), fetchRecentTradeReviews({ limit: 20 })])
      setHealth(h)
      setReviews(r)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  async function handleSymbolReview() {
    if (!symbol.trim()) return
    setGenerating(true)
    setErrorMessage('')
    try {
      const result = await startSymbolReviewTask({ symbol: symbol.trim() })
      setSelectedReview(result)
      setReviews((prev) => [result, ...prev.filter((r) => r.id !== result.id)])
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Review failed')
    } finally {
      setGenerating(false)
    }
  }

  async function handleSingleReview() {
    if (!tradeId.trim() || !symbol.trim()) return
    setGenerating(true)
    setErrorMessage('')
    try {
      const result = await startSingleTradeReviewTask(tradeId.trim(), symbol.trim())
      setSelectedReview(result)
      setReviews((prev) => [result, ...prev.filter((r) => r.id !== result.id)])
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Review failed')
    } finally {
      setGenerating(false)
    }
  }

  async function handleSelectReview(id: string) {
    try {
      setSelectedReview(await fetchTradeReviewDetail(id))
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load review')
    }
  }

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">Loading...</div></div></section>
  }

  const output = selectedReview?.review_output
  const reviewData = typeof output === 'string' ? (() => { try { return JSON.parse(output) } catch { return null } })() : output

  return (
    <section className="page-section">
      {/* Header */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">AI AGENT</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>Trade Review</h2>
              <p className="panel-subtitle">Review past trades for performance evaluation and improvement insights.</p>
            </div>
            {health && (
              <span className={`tag ${health.llm_configured ? 'tag--positive' : 'tag--negative'}`}>
                {health.llm_configured ? 'LLM READY' : 'LLM MISSING'}
              </span>
            )}
          </div>
        </div>
      </section>

      {errorMessage && (
        <div style={{ padding: '12px 16px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>
          {errorMessage}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4 }}>
        {(['symbol', 'single'] as const).map((tab) => (
          <button key={tab} className={`btn btn--sm ${activeTab === tab ? 'is-active' : ''}`}
            onClick={() => setActiveTab(tab)}
            style={{
              borderRadius: 'var(--radius-sm)',
              background: activeTab === tab ? 'rgba(212,168,67,0.08)' : 'transparent',
              borderColor: activeTab === tab ? 'rgba(212,168,67,0.2)' : 'transparent',
              color: activeTab === tab ? 'var(--color-accent-strong)' : 'var(--color-text-secondary)',
            }}>
            {tab === 'symbol' ? 'Symbol Review' : 'Single Trade Review'}
          </button>
        ))}
      </div>

      {/* Input Form */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          {activeTab === 'symbol' ? (
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
              <label className="field-stack" style={{ flex: 1 }}>
                <span className="field-stack__label">Symbol</span>
                <input className="input" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="AAPL" />
              </label>
              <button className="btn btn--accent" onClick={handleSymbolReview} disabled={generating || !symbol.trim()}>
                {generating ? 'Generating...' : 'Generate Review'}
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
              <label className="field-stack" style={{ flex: 1 }}>
                <span className="field-stack__label">Symbol</span>
                <input className="input" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="AAPL" />
              </label>
              <label className="field-stack" style={{ flex: 1 }}>
                <span className="field-stack__label">Trade ID</span>
                <input className="input" value={tradeId} onChange={(e) => setTradeId(e.target.value)} placeholder="Trade ID" />
              </label>
              <button className="btn btn--accent" onClick={handleSingleReview} disabled={generating || !symbol.trim() || !tradeId.trim()}>
                {generating ? 'Generating...' : 'Generate Review'}
              </button>
            </div>
          )}
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 'var(--space-4)' }}>
        {/* Recent reviews list */}
        <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.2s both' }}>
          <div className="surface-panel__content" style={{ padding: '16px' }}>
            <p className="eyebrow" style={{ marginBottom: 8 }}>RECENT REVIEWS ({reviews.length})</p>
            <div style={{ display: 'grid', gap: 6, maxHeight: 400, overflow: 'auto' }}>
              {reviews.length === 0 ? (
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>No reviews yet.</p>
              ) : (
                reviews.map((r) => (
                  <button key={r.id} className="btn btn--ghost btn--sm"
                    onClick={() => handleSelectReview(r.id)}
                    style={{
                      justifyContent: 'flex-start', textAlign: 'left',
                      borderRadius: 'var(--radius-sm)',
                      background: selectedReview?.id === r.id ? 'rgba(212,168,67,0.08)' : 'transparent',
                      borderColor: selectedReview?.id === r.id ? 'rgba(212,168,67,0.2)' : 'transparent',
                    }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.85rem' }}>{r.symbol || r.review_type}</span>
                    <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{r.review_type}</span>
                  </button>
                ))
              )}
            </div>
          </div>
        </section>

        {/* Review detail */}
        <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.3s both' }}>
          <div className="surface-panel__content">
            {!selectedReview ? (
              <div className="empty-state" style={{ minHeight: 300 }}>Select a review or generate a new one.</div>
            ) : !reviewData ? (
              <div className="empty-state" style={{ minHeight: 300 }}>Review data could not be parsed.</div>
            ) : (
              <div style={{ display: 'grid', gap: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <p className="eyebrow" style={{ margin: 0 }}>{selectedReview.symbol || selectedReview.review_type}</p>
                  {reviewData.overall_score != null && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 700, color: 'var(--color-accent-strong)' }}>{reviewData.overall_score}/100</span>
                  )}
                  {reviewData.rating && (
                    <span className={`tag ${reviewData.rating === 'excellent' ? 'tag--positive' : reviewData.rating === 'poor' ? 'tag--negative' : ''}`}>{reviewData.rating}</span>
                  )}
                </div>

                {reviewData.summary && (
                  <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>{reviewData.summary}</p>
                )}

                {reviewData.strengths?.length > 0 && (
                  <div>
                    <p className="eyebrow" style={{ color: 'var(--color-positive)' }}>STRENGTHS</p>
                    <ul style={{ margin: '4px 0 0', padding: '0 0 0 16px', color: 'var(--color-text-secondary)', fontSize: '0.88rem' }}>
                      {reviewData.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}

                {reviewData.weaknesses?.length > 0 && (
                  <div>
                    <p className="eyebrow" style={{ color: 'var(--color-negative)' }}>WEAKNESSES</p>
                    <ul style={{ margin: '4px 0 0', padding: '0 0 0 16px', color: 'var(--color-text-secondary)', fontSize: '0.88rem' }}>
                      {reviewData.weaknesses.map((w: string, i: number) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                )}

                {reviewData.improvement_suggestions?.length > 0 && (
                  <div>
                    <p className="eyebrow">IMPROVEMENTS</p>
                    <ul style={{ margin: '4px 0 0', padding: '0 0 0 16px', color: 'var(--color-text-secondary)', fontSize: '0.88rem' }}>
                      {reviewData.improvement_suggestions.map((s: string, i: number) => <li key={i}>{s}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </section>
  )
}
