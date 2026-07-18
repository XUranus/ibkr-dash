/** Trade review page -- list and view trade reviews. */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { request } from '@/api/http'
import { safeJsonParse } from '@/utils/safeJson'
import type { TradeReviewResult } from '@/types/tradeReview'
import AgentEvidencePanel from '@/components/AgentEvidencePanel'

export default function TradeReviewView() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language?.startsWith('zh') ? 'zh' : 'en'
  const [reviews, setReviews] = useState<TradeReviewResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedReview, setSelectedReview] = useState<TradeReviewResult | null>(null)

  // Generate form state
  const [symbol, setSymbol] = useState('')
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')

  const loadReviews = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await request<{ items: TradeReviewResult[] }>(`/api/trade-review/reviews?lang=${lang}`)
      setReviews(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : t('tradeReviewPage.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [t, lang])

  useEffect(() => { void loadReviews() }, [loadReviews])

  useEffect(() => {
    if (!selectedId) {
      setSelectedReview(null)
      return
    }
    const review = reviews.find((r) => r.id === selectedId) || null
    setSelectedReview(review)
  }, [selectedId, reviews])

  const handleGenerate = async () => {
    if (!symbol.trim()) return
    setGenerating(true)
    setGenerateError('')
    try {
      await request('/api/trade-review/review', {
        method: 'POST',
        body: JSON.stringify({ symbol: symbol.trim().toUpperCase() }),
      })
      setSymbol('')
      await loadReviews()
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : t('tradeReviewPage.generateFailed'))
    } finally {
      setGenerating(false)
    }
  }

  return (
    <section className="page-section" style={{ animation: 'slideUp 0.4s ease' }}>
      <header style={{ marginBottom: 'var(--space-6)' }}>
        <p className="eyebrow">{t('tradeReviewPage.eyebrow')}</p>
        <h1 className="page-title">{t('tradeReviewPage.title')}</h1>
        <p className="page-subtitle">{t('tradeReviewPage.subtitle')}</p>
      </header>

      {/* Generate form */}
      <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '16px' }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder={t('tradeReviewPage.symbolPlaceholder')}
            style={{
              flex: 1,
              padding: '8px 12px',
              background: 'var(--color-surface)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--color-text-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.85rem',
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
          />
          <button
            className="btn btn--accent"
            onClick={handleGenerate}
            disabled={generating || !symbol.trim()}
          >
            {generating ? t('tradeReviewPage.generating') : t('tradeReviewPage.generate')}
          </button>
        </div>
        {generateError && (
          <p style={{ color: 'var(--color-negative)', fontSize: '0.82rem', marginTop: 8 }}>{generateError}</p>
        )}
      </div>

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
              {t('tradeReviewPage.reviewCount', { count: reviews.length })}
            </p>
            {loading ? (
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>{t('tradeReviewPage.loading')}</p>
            ) : reviews.length === 0 ? (
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>{t('tradeReviewPage.noReviews')}</p>
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
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>{t('tradeReviewPage.selectReview')}</p>
              </div>
            ) : (
              <div>
                <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
                  <h3 style={{ margin: 0 }}>{selectedReview.symbol || t('tradeReviewPage.title')}</h3>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                    {selectedReview.review_type}
                  </span>
                </div>
                <div style={{ marginBottom: 16, padding: 12, background: 'rgba(10,14,26,0.5)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '0.85rem', lineHeight: 1.7 }}>
                    <div style={{ marginBottom: 8 }}>
                      <strong style={{ color: 'var(--color-accent-strong)' }}>{t('tradeReviewPage.overallScore')}:</strong>
                      <span style={{ marginLeft: 8 }}>{selectedReview.rating} (Score: {selectedReview.overall_score})</span>
                    </div>
                    <div style={{ marginBottom: 8 }}>
                      <strong style={{ color: 'var(--color-accent-strong)' }}>{t('tradeReviewPage.summary')}</strong>
                      <p style={{ margin: '4px 0 0' }}>{selectedReview.summary}</p>
                    </div>
                    {(selectedReview.strengths?.length ?? 0) > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <strong style={{ color: 'var(--color-positive)' }}>{t('tradeReviewPage.strengths')}</strong>
                        <ul style={{ margin: '4px 0 0 16px' }}>
                          {selectedReview.strengths!.map((s, i) => <li key={i}>{s}</li>)}
                        </ul>
                      </div>
                    )}
                    {(selectedReview.weaknesses?.length ?? 0) > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <strong style={{ color: 'var(--color-negative)' }}>{t('tradeReviewPage.weaknesses')}</strong>
                        <ul style={{ margin: '4px 0 0 16px' }}>
                          {selectedReview.weaknesses!.map((w, i) => <li key={i}>{w}</li>)}
                        </ul>
                      </div>
                    )}
                    {(selectedReview.improvement_suggestions?.length ?? 0) > 0 && (
                      <div>
                        <strong style={{ color: 'var(--color-accent-strong)' }}>{t('tradeReviewPage.improvements')}</strong>
                        <ul style={{ margin: '4px 0 0 16px' }}>
                          {selectedReview.improvement_suggestions!.map((s, i) => <li key={i}>{s}</li>)}
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
