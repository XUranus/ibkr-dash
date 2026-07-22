/** Daily position review page -- calendar view with review content. */

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { request } from '@/api/http'
import { safeJsonParse } from '@/utils/safeJson'
import type { DailyPositionReviewResult } from '@/types/dailyPositionReview'
import AgentEvidencePanel from '@/components/AgentEvidencePanel'

/** Simple Markdown to HTML converter for review display */
function simpleMarkdownToHtml(md: string): string {
  return md
    // Headers
    .replace(/^### (.+)$/gm, '<h3 style="margin:16px 0 8px;color:var(--color-accent-strong);font-size:1rem;">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 style="margin:20px 0 10px;color:var(--color-accent-strong);font-size:1.1rem;">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 style="margin:0 0 16px;color:var(--color-text-bright);font-size:1.3rem;">$1</h1>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong style="color:var(--color-text-bright);">$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em style="color:var(--color-text-secondary);">$1</em>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr style="border:none;border-top:1px solid var(--color-border);margin:16px 0;">')
    // List items
    .replace(/^- (.+)$/gm, '<li style="margin:4px 0;margin-left:20px;">$1</li>')
    // Paragraphs (lines that aren't already wrapped)
    .replace(/^(?!<[hbl]|<li|<hr|<p)(.+)$/gm, '<p style="margin:4px 0;">$1</p>')
    // Clean up empty paragraphs
    .replace(/<p style="margin:4px 0;"><\/p>/g, '')
}

/** Trading date info from API */
interface TradingDateInfo {
  date: string
  has_data: boolean
  has_review: boolean
}

/** Calendar day cell data */
interface CalendarDay {
  date: Date
  dateStr: string
  dayOfMonth: number
  isCurrentMonth: boolean
  isToday: boolean
  hasData: boolean
  hasReview: boolean
}

/** Get days in a month */
function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

/** Get day of week for first day of month (0 = Sunday) */
function getFirstDayOfWeek(year: number, month: number): number {
  return new Date(year, month, 1).getDay()
}

/** Format date as YYYY-MM-DD */
function formatDate(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

/** Parse YYYY-MM-DD to Date */
function parseDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export default function DailyPositionReviewView() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language?.startsWith('zh') ? 'zh' : 'en'

  // Calendar state
  const today = new Date()
  const [currentYear, setCurrentYear] = useState(today.getFullYear())
  const [currentMonth, setCurrentMonth] = useState(today.getMonth())

  // Data state
  const [tradingDates, setTradingDates] = useState<TradingDateInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Selected date state
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [selectedReview, setSelectedReview] = useState<DailyPositionReviewResult | null>(null)
  const [loadingReview, setLoadingReview] = useState(false)

  // Generate state
  const [generating, setGenerating] = useState(false)
  const [generateError, setGenerateError] = useState('')

  // Load trading dates for current month
  const loadTradingDates = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await request<{ items: TradingDateInfo[] }>(
        `/api/daily-position-review/trading-dates?year=${currentYear}&month=${currentMonth + 1}`
      )
      setTradingDates(data.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : t('dailyPositionReview.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [currentYear, currentMonth, t])

  useEffect(() => { void loadTradingDates() }, [loadTradingDates])

  // Load review for selected date
  useEffect(() => {
    if (!selectedDate) {
      setSelectedReview(null)
      return
    }

    const tradingDate = tradingDates.find(d => d.date === selectedDate)
    if (!tradingDate?.has_review) {
      setSelectedReview(null)
      return
    }

    const loadReview = async () => {
      setLoadingReview(true)
      try {
        const data = await request<DailyPositionReviewResult>(
          `/api/daily-position-review/reviews/${selectedDate}?lang=${lang}`
        )
        setSelectedReview(data)
      } catch (err) {
        console.error('Failed to load review:', err)
        setSelectedReview(null)
      } finally {
        setLoadingReview(false)
      }
    }

    void loadReview()
  }, [selectedDate, tradingDates, lang])

  // Generate calendar days
  const calendarDays = useMemo((): CalendarDay[] => {
    const days: CalendarDay[] = []
    const daysInMonth = getDaysInMonth(currentYear, currentMonth)
    const firstDayOfWeek = getFirstDayOfWeek(currentYear, currentMonth)

    // Previous month's trailing days
    const prevMonth = currentMonth === 0 ? 11 : currentMonth - 1
    const prevYear = currentMonth === 0 ? currentYear - 1 : currentYear
    const daysInPrevMonth = getDaysInMonth(prevYear, prevMonth)

    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
      const day = daysInPrevMonth - i
      const date = new Date(prevYear, prevMonth, day)
      days.push({
        date,
        dateStr: formatDate(date),
        dayOfMonth: day,
        isCurrentMonth: false,
        isToday: false,
        hasData: false,
        hasReview: false,
      })
    }

    // Current month's days
    const todayStr = formatDate(today)
    for (let day = 1; day <= daysInMonth; day++) {
      const date = new Date(currentYear, currentMonth, day)
      const dateStr = formatDate(date)
      const tradingDate = tradingDates.find(d => d.date === dateStr)
      days.push({
        date,
        dateStr,
        dayOfMonth: day,
        isCurrentMonth: true,
        isToday: dateStr === todayStr,
        hasData: tradingDate?.has_data ?? false,
        hasReview: tradingDate?.has_review ?? false,
      })
    }

    // Next month's leading days (fill to complete the grid)
    const remaining = 42 - days.length // 6 rows × 7 days
    const nextMonth = currentMonth === 11 ? 0 : currentMonth + 1
    const nextYear = currentMonth === 11 ? currentYear + 1 : currentYear

    for (let day = 1; day <= remaining; day++) {
      const date = new Date(nextYear, nextMonth, day)
      days.push({
        date,
        dateStr: formatDate(date),
        dayOfMonth: day,
        isCurrentMonth: false,
        isToday: false,
        hasData: false,
        hasReview: false,
      })
    }

    return days
  }, [currentYear, currentMonth, tradingDates])

  // Navigate to previous month
  const goToPrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11)
      setCurrentYear(currentYear - 1)
    } else {
      setCurrentMonth(currentMonth - 1)
    }
    setSelectedDate(null)
  }

  // Navigate to next month
  const goToNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0)
      setCurrentYear(currentYear + 1)
    } else {
      setCurrentMonth(currentMonth + 1)
    }
    setSelectedDate(null)
  }

  // Generate review for a date
  const handleGenerate = async (date: string) => {
    setGenerating(true)
    setGenerateError('')
    try {
      await request('/api/daily-position-review/generate', {
        method: 'POST',
        body: JSON.stringify({ report_date: date }),
      })
      // Reload trading dates to update review status
      await loadTradingDates()
      // Select the newly generated review
      setSelectedDate(date)
    } catch (err) {
      setGenerateError(err instanceof Error ? err.message : t('dailyPositionReview.generateFailed'))
    } finally {
      setGenerating(false)
    }
  }

  // Delete review
  const handleDelete = async (date: string) => {
    if (!confirm(t('dailyPositionReview.confirmDelete', { date }))) return
    try {
      await request(`/api/daily-position-review/reviews/${date}`, { method: 'DELETE' })
      if (selectedDate === date) {
        setSelectedDate(null)
        setSelectedReview(null)
      }
      await loadTradingDates()
    } catch (err) {
      alert(err instanceof Error ? err.message : t('dailyPositionReview.deleteFailed'))
    }
  }

  // Render review content
  const renderReviewContent = (review: DailyPositionReviewResult): React.ReactNode => {
    // Use unified markdown content if available
    const markdownContent = (review as Record<string, unknown>).review_markdown as string | undefined

    if (markdownContent) {
      return (
        <div
          className="markdown-content"
          style={{
            fontSize: '0.9rem',
            lineHeight: 1.8,
            color: 'var(--color-text-primary)',
            whiteSpace: 'pre-wrap',
          }}
          dangerouslySetInnerHTML={{ __html: simpleMarkdownToHtml(markdownContent) }}
        />
      )
    }

    // Fallback to structured display
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

  // Get selected trading date info
  const selectedTradingDate = tradingDates.find(d => d.date === selectedDate)

  // Month names
  const monthNames = lang === 'zh'
    ? ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
    : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

  const dayHeaders = lang === 'zh'
    ? ['日', '一', '二', '三', '四', '五', '六']
    : ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

  return (
    <section className="page-section">
      {/* Header */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <p className="eyebrow">{t('dailyPositionReview.eyebrow')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('dailyPositionReview.title')}</h2>
              <p className="panel-subtitle">{t('dailyPositionReview.subtitle')}</p>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '12px 16px', borderLeft: '3px solid var(--color-negative)' }}>
          <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{error}</p>
        </div>
      )}

      {/* Main content: Calendar + Review */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 'var(--space-4)', alignItems: 'start' }}>
        {/* Left: Calendar */}
        <div className="surface-panel">
          <div className="surface-panel__content" style={{ padding: 16 }}>
            {/* Month navigation */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <button
                className="btn btn--ghost btn--sm"
                onClick={goToPrevMonth}
                style={{ padding: '4px 8px', fontSize: '1rem' }}
              >
                ←
              </button>
              <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text-bright)' }}>
                {currentYear} {monthNames[currentMonth]}
              </h3>
              <button
                className="btn btn--ghost btn--sm"
                onClick={goToNextMonth}
                style={{ padding: '4px 8px', fontSize: '1rem' }}
              >
                →
              </button>
            </div>

            {/* Day headers */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4, marginBottom: 8 }}>
              {dayHeaders.map((header) => (
                <div
                  key={header}
                  style={{
                    textAlign: 'center',
                    fontSize: '0.72rem',
                    color: 'var(--color-text-muted)',
                    fontFamily: 'var(--font-mono)',
                    padding: '4px 0',
                  }}
                >
                  {header}
                </div>
              ))}
            </div>

            {/* Calendar grid */}
            {loading ? (
              <div style={{ textAlign: 'center', padding: '20px 0', color: 'var(--color-text-muted)', fontSize: '0.82rem' }}>
                {t('dailyPositionReview.loading')}
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
                {calendarDays.map((day) => {
                  const isSelected = selectedDate === day.dateStr
                  const isClickable = day.isCurrentMonth && day.hasData
                  const hasReview = day.hasReview

                  return (
                    <div
                      key={day.dateStr}
                      onClick={() => {
                        if (isClickable) setSelectedDate(day.dateStr)
                      }}
                      style={{
                        position: 'relative',
                        padding: '6px 2px',
                        textAlign: 'center',
                        fontSize: '0.78rem',
                        fontFamily: 'var(--font-mono)',
                        borderRadius: 'var(--radius-sm)',
                        cursor: isClickable ? 'pointer' : 'default',
                        background: isSelected
                          ? 'rgba(212,168,67,0.15)'
                          : day.isToday
                            ? 'rgba(100,150,255,0.08)'
                            : 'transparent',
                        border: isSelected
                          ? '1px solid rgba(212,168,67,0.4)'
                          : '1px solid transparent',
                        color: !day.isCurrentMonth
                          ? 'var(--color-text-muted)'
                          : isClickable
                            ? 'var(--color-text-primary)'
                            : 'var(--color-text-muted)',
                        opacity: day.isCurrentMonth ? 1 : 0.4,
                        transition: 'all 0.15s ease',
                      }}
                    >
                      <span>{day.dayOfMonth}</span>
                      {/* Status indicator */}
                      {day.isCurrentMonth && (
                        <div style={{
                          position: 'absolute',
                          bottom: 2,
                          left: '50%',
                          transform: 'translateX(-50%)',
                          width: 4,
                          height: 4,
                          borderRadius: '50%',
                          background: !day.hasData
                            ? 'var(--color-text-muted)' // No data
                            : hasReview
                              ? 'var(--color-positive)' // Has review
                              : 'var(--color-accent)', // Has data, no review
                          opacity: 0.7,
                        }} />
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {/* Legend */}
            <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-positive)', opacity: 0.7 }} />
                  <span>{t('dailyPositionReview.hasReview')}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-accent)', opacity: 0.7 }} />
                  <span>{t('dailyPositionReview.noReview')}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--color-text-muted)', opacity: 0.7 }} />
                  <span>{t('dailyPositionReview.noData')}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Review content */}
        <div className="surface-panel">
          <div className="surface-panel__content" style={{ padding: 20, minHeight: 400 }}>
            {!selectedDate ? (
              <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
                  {t('dailyPositionReview.selectDate')}
                </p>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', marginTop: 8 }}>
                  {t('dailyPositionReview.selectDateHint')}
                </p>
              </div>
            ) : loadingReview ? (
              <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                  {t('dailyPositionReview.loadingReview')}
                </p>
              </div>
            ) : selectedReview ? (
              <div>
                {/* Review header with actions */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--color-text-bright)' }}>
                    {t('dailyPositionReview.review')}: {selectedDate}
                  </h3>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      className="btn btn--ghost btn--sm"
                      onClick={() => handleGenerate(selectedDate)}
                      disabled={generating}
                      style={{ fontSize: '0.78rem' }}
                    >
                      {generating ? t('dailyPositionReview.generating') : t('dailyPositionReview.regenerate')}
                    </button>
                    <button
                      className="btn btn--ghost btn--sm"
                      onClick={() => handleDelete(selectedDate)}
                      style={{ color: 'var(--color-negative)', fontSize: '0.78rem' }}
                    >
                      {t('dailyPositionReview.delete')}
                    </button>
                  </div>
                </div>

                {generateError && (
                  <p style={{ color: 'var(--color-negative)', fontSize: '0.82rem', marginBottom: 12 }}>{generateError}</p>
                )}

                {/* Review content */}
                <div style={{
                  padding: 16,
                  background: 'rgba(10,14,26,0.5)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--color-border)',
                }}>
                  {renderReviewContent(selectedReview)}
                </div>

                {/* Evidence panel */}
                {selectedReview.evidence_summary && (
                  <div style={{ marginTop: 16 }}>
                    <AgentEvidencePanel
                      evidenceSummary={safeJsonParse(selectedReview.evidence_summary, {})}
                    />
                  </div>
                )}
              </div>
            ) : selectedTradingDate?.has_data && !selectedTradingDate?.has_review ? (
              // No review yet, show generate button
              <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem', marginBottom: 16 }}>
                  {t('dailyPositionReview.noReviewForDate', { date: selectedDate })}
                </p>
                <button
                  className="btn btn--accent"
                  onClick={() => handleGenerate(selectedDate)}
                  disabled={generating}
                  style={{ minWidth: 160 }}
                >
                  {generating ? t('dailyPositionReview.generating') : t('dailyPositionReview.generateForDate')}
                </button>
                {generateError && (
                  <p style={{ color: 'var(--color-negative)', fontSize: '0.82rem', marginTop: 12 }}>{generateError}</p>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                  {t('dailyPositionReview.noDataForDate')}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
