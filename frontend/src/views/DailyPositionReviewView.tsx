/** Daily position review page -- list and view daily position reviews. */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { request } from '@/api/http'
import { safeJsonParse } from '@/utils/safeJson'
import type { DailyPositionReviewResult } from '@/types/dailyPositionReview'
import AgentEvidencePanel from '@/components/AgentEvidencePanel'

export default function DailyPositionReviewView() {
  const { t } = useTranslation()
  const [reviews, setReviews] = useState<DailyPositionReviewResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [selectedReview, setSelectedReview] = useState<DailyPositionReviewResult | null>(null)

  const loadReviews = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await request<{ items: DailyPositionReviewResult[] }>('/api/daily-position-review')
      setReviews(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : t('dailyPositionReview.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { void loadReviews() }, [loadReviews])

  useEffect(() => {
    if (!selectedId) {
      setSelectedReview(null)
      return
    }
    const review = reviews.find((r) => r.id === selectedId) || null
    setSelectedReview(review)
  }, [selectedId, reviews])

  function renderReviewDetail(review: DailyPositionReviewResult): React.ReactNode {
    return (
      <div style={{ fontSize: '0.85rem', lineHeight: 1.7 }}>
        <div style={{ marginBottom: 12 }}>
          <strong style={{ color: 'var(--color-accent-strong)' }}>{t('dailyPositionReview.summary')}</strong>
          <p style={{ margin: '4px 0 0', color: 'var(--color-text-primary)' }}>{review.summary}</p>
        </div>
        <div style={{ marginBottom: 12 }}>
          <strong style={{ color: 'var(--color-accent-strong)' }}>{t('dailyPositionReview.accountConclusion')}</strong>
          <p style={{ margin: '4px 0 0', color: 'var(--color-text-primary)' }}>{review.account_conclusion}</p>
        </div>
        <div style={{ marginBottom: 12 }}>
          <strong style={{ color: 'var(--color-accent-strong)' }}>{t('dailyPositionReview.riskAnalysis')}</strong>
          <p style={{ margin: '4px 0 0', color: 'var(--color-text-primary)' }}>{review.risk_analysis}</p>
        </div>
        <div style={{ marginBottom: 12 }}>
          <strong style={{ color: 'var(--color-accent-strong)' }}>{t('dailyPositionReview.marketContext')}</strong>
          <p style={{ margin: '4px 0 0', color: 'var(--color-text-primary)' }}>{review.market_context}</p>
        </div>
        <div style={{ marginBottom: 12 }}>
          <strong style={{ color: 'var(--color-accent-strong)' }}>{t('dailyPositionReview.operationObservation')}</strong>
          <p style={{ margin: '4px 0 0', color: 'var(--color-text-primary)' }}>{review.operation_observation}</p>
        </div>
      </div>
    )
  }

  return (
    <section className="page-section" style={{ animation: 'slideUp 0.4s ease' }}>
      <header style={{ marginBottom: 'var(--space-6)' }}>
        <p className="eyebrow">{t('dailyPositionReview.eyebrow')}</p>
        <h1 className="page-title">{t('dailyPositionReview.title')}</h1>
        <p className="page-subtitle">{t('dailyPositionReview.subtitle')}</p>
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
              {t('dailyPositionReview.reviewCount', { count: reviews.length })}
            </p>
            {loading ? (
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>{t('dailyPositionReview.loading')}</p>
            ) : reviews.length === 0 ? (
              <p style={{ color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>{t('dailyPositionReview.noReviews')}</p>
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
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)', marginRight: 8 }}>
                    {r.report_date}
                  </span>
                  <span style={{ color: 'var(--color-text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {r.id.slice(0, 12)}...
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
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>{t('dailyPositionReview.selectReview')}</p>
              </div>
            ) : (
              <div>
                <h3 style={{ marginBottom: 12 }}>
                  {t('dailyPositionReview.review')}: {selectedReview.report_date}
                </h3>
                <div style={{ marginBottom: 16, padding: 12, background: 'rgba(10,14,26,0.5)', borderRadius: 'var(--radius-sm)' }}>
                  {renderReviewDetail(selectedReview)}
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
