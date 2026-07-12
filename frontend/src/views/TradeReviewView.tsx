/** Trade review page -- list and view trade reviews. */

import { useState, useEffect, useCallback } from 'react'
import { request } from '@/api/http'
import { safeJsonParse } from '@/utils/safeJson'
import type { TradeReviewResult } from '@/types/tradeReview'
import AgentEvidencePanel from '@/components/AgentEvidencePanel'

export default function TradeReviewView() {
  const [reviews, setReviews] = useState<TradeReviewResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedReview, setSelectedReview] = useState<TradeReviewResult | null>(null)

  const loadReviews = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await request<{ items: TradeReviewResult[] }>('/api/trade-review/reviews')
      setReviews(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trade reviews')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadReviews() }, [loadReviews])

  useEffect(() => {
    if (!selectedId) {
      setSelectedReview(null)
      return
    }
    const review = reviews.find((r) => r.id === selectedId) || null
    setSelectedReview(review)
  }, [selectedId, reviews])

  return (
    <section className="page-section" style={{ animation: 'slideUp 0.4s ease' }}>
      <header style={{ marginBottom: 'var(--space-6)' }}>
        <p className="eyebrow">Agent</p>
        <h1 className="page-title">Trade Review</h1>
        <p className="page-subtitle">AI-powered trade analysis and behavioral insights</p>
      </header>

      {error && (
        <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '12px 16px', borderLeft: '3px solid var(--color-negative)' }}>
          <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{error}</p>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 'var(--space-4)' }}>
        {/* Review list */}
        <div className="surface-panel">
          <div className="surface-panel__content" style={{ padding: 12, maxHeight: '70vh', overflow: 'auto' }}>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: 8 }}>
              {reviews.length} REVIEW(S)
            </p>
            {loading ? (
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>Loading...</p>
            ) : reviews.length === 0 ? (
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>No trade reviews found.</p>
            ) : (
              reviews.map((r) => (
                <button
                  key={r.id}
                  className="btn btn--ghost btn--sm"
                  onClick={() => setSelectedId(r.id)}
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    textAlign: 'left',
                    marginBottom: 4,
                    background: selectedId === r.id ? 'rgba(212,168,67,0.08)' : 'transparent',
                    borderColor: selectedId === r.id ? 'rgba(212,168,67,0.2)' : 'transparent',
                    fontSize: '0.82rem',
                  }}
                >
                  <span style={{ color: 'var(--color-accent-strong)', marginRight: 8 }}>{r.symbol || '--'}</span>
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
                    {r.review_type}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Review detail */}
        <div className="surface-panel">
          <div className="surface-panel__content" style={{ padding: 16 }}>
            {!selectedReview ? (
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>Select a review to view details</p>
              </div>
            ) : (
              <div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
                  <h3 style={{ margin: 0 }}>{selectedReview.symbol || 'Trade Review'}</h3>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                    {selectedReview.review_type}
                  </span>
                </div>
                <div style={{ marginBottom: 16, padding: 12, background: 'rgba(10,14,26,0.5)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.85rem', lineHeight: 1.7 }}>
                    <div style={{ marginBottom: 8 }}>
                      <strong style={{ color: 'var(--color-accent-strong)' }}>Rating:</strong>
                      <span style={{ marginLeft: 8 }}>{selectedReview.rating} (Score: {selectedReview.overall_score})</span>
                    </div>
                    <div style={{ marginBottom: 8 }}>
                      <strong style={{ color: 'var(--color-accent-strong)' }}>Summary:</strong>
                      <p style={{ margin: '4px 0 0' }}>{selectedReview.summary}</p>
                    </div>
                    {selectedReview.strengths.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <strong style={{ color: 'var(--color-positive)' }}>Strengths:</strong>
                        <ul style={{ margin: '4px 0 0 16px' }}>
                          {selectedReview.strengths.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      </div>
                    )}
                    {selectedReview.weaknesses.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <strong style={{ color: 'var(--color-negative)' }}>Weaknesses:</strong>
                        <ul style={{ margin: '4px 0 0 16px' }}>
                          {selectedReview.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                        </ul>
                      </div>
                    )}
                    {selectedReview.improvement_suggestions.length > 0 && (
                      <div>
                        <strong style={{ color: 'var(--color-accent-strong)' }}>Suggestions:</strong>
                        <ul style={{ margin: '4px 0 0 16px' }}>
                          {selectedReview.improvement_suggestions.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                </div>
                {selectedReview.evidence_summary && (
                  <AgentEvidencePanel
                    evidenceSummary={safeJsonParse(selectedReview.evidence_summary, {})}
                  />
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
