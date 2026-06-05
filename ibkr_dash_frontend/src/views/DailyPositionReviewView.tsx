import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchDailyPositionReviewHealth, fetchDailyPositionReviewDates, fetchDailyPositionReview, startDailyPositionReviewTask } from '@/api/dailyPositionReview'
import type { DailyPositionReviewHealth, DailyPositionReviewResult } from '@/types/dailyPositionReview'

export default function DailyPositionReviewView() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [health, setHealth] = useState<DailyPositionReviewHealth | null>(null)
  const [dates, setDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [review, setReview] = useState<DailyPositionReviewResult | null>(null)
  const [generating, setGenerating] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const [h, d] = await Promise.all([fetchDailyPositionReviewHealth(), fetchDailyPositionReviewDates()])
      setHealth(h)
      setDates(d)
      if (d.length > 0) {
        setSelectedDate(d[0])
        setReview(await fetchDailyPositionReview(d[0]))
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('dailyReview.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  async function handleSelectDate(date: string) {
    setSelectedDate(date)
    setErrorMessage('')
    try {
      setReview(await fetchDailyPositionReview(date))
    } catch {
      setReview(null)
    }
  }

  async function handleGenerate() {
    const date = selectedDate || new Date().toISOString().split('T')[0]
    setGenerating(true)
    setErrorMessage('')
    try {
      const result = await startDailyPositionReviewTask(date)
      setReview(result)
      if (!dates.includes(date)) {
        setDates((prev) => [date, ...prev])
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('dailyReview.generationFailed'))
    } finally {
      setGenerating(false)
    }
  }

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">{t('common.loading')}</div></div></section>
  }

  const output = review?.review_output
  const reviewData = typeof output === 'string' ? (() => { try { return JSON.parse(output) } catch { return null } })() : output

  return (
    <section className="page-section">
      {/* Header */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{t('dailyReview.aiAgent')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('dailyReview.title')}</h2>
              <p className="panel-subtitle">{t('dailyReview.subtitle')}</p>
            </div>
            {health && (
              <span className={`tag ${health.llm_configured ? 'tag--positive' : 'tag--negative'}`}>
                {health.llm_configured ? t('dailyReview.llmReady') : t('dailyReview.llmMissing')}
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

      {/* Controls */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
            <label className="field-stack" style={{ flex: 1 }}>
              <span className="field-stack__label">{t('dailyReview.reportDate')}</span>
              <select className="select" value={selectedDate} onChange={(e) => handleSelectDate(e.target.value)}>
                <option value="">{t('dailyReview.selectDate')}</option>
                {dates.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </label>
            <button className="btn btn--accent" onClick={handleGenerate} disabled={generating}>
              {generating ? t('dailyReview.generating') : t('dailyReview.generateReview')}
            </button>
          </div>
        </div>
      </section>

      {/* Review Content */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.2s both' }}>
        <div className="surface-panel__content">
          {!review ? (
            <div className="empty-state" style={{ minHeight: 300 }}>{t('dailyReview.selectOrGenerate')}</div>
          ) : !reviewData ? (
            <div className="empty-state" style={{ minHeight: 300 }}>{t('dailyReview.reviewDataParseError')}</div>
          ) : (
            <div style={{ display: 'grid', gap: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <p className="eyebrow" style={{ margin: 0 }}>{t('dailyReview.dailyReviewLabel')}</p>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>{review.report_date}</span>
              </div>

              {reviewData.summary && (
                <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>{reviewData.summary}</p>
              )}

              {reviewData.account_conclusion && (
                <div>
                  <p className="eyebrow">{t('dailyReview.accountConclusion')}</p>
                  <p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: '0.88rem', lineHeight: 1.6 }}>{reviewData.account_conclusion}</p>
                </div>
              )}

              {reviewData.attribution_summary && (
                <div>
                  <p className="eyebrow">{t('dailyReview.attribution')}</p>
                  <p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: '0.88rem', lineHeight: 1.6 }}>{reviewData.attribution_summary}</p>
                </div>
              )}

              {reviewData.focus_symbol_analyses?.length > 0 && (
                <div>
                  <p className="eyebrow">{t('dailyReview.focusSymbols')}</p>
                  <div style={{ display: 'grid', gap: 8, marginTop: 4 }}>
                    {reviewData.focus_symbol_analyses.map((s: Record<string, unknown>, i: number) => (
                      <div key={i} style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(10,14,26,0.4)', border: '1px solid var(--color-border-subtle)' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-text-bright)' }}>{String(s.symbol ?? '')}</span>
                        <p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>{String(s.analysis ?? s.summary ?? '')}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {reviewData.tomorrow_watchlist?.length > 0 && (
                <div>
                  <p className="eyebrow">{t('dailyReview.watchlist')}</p>
                  <ul style={{ margin: '4px 0 0', padding: '0 0 0 16px', color: 'var(--color-text-secondary)', fontSize: '0.88rem' }}>
                    {reviewData.tomorrow_watchlist.map((w: string | Record<string, unknown>, i: number) => (
                      <li key={i}>{typeof w === 'string' ? w : JSON.stringify(w)}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </section>
  )
}
