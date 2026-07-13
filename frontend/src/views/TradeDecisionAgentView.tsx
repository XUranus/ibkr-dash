import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { analyzeEntryDecision, analyzeHoldingDecision, fetchRecentTradeDecisions, fetchTradeDecisionDetail, fetchTradeDecisionHealth, fetchTradeDecisionReport } from '@/api/tradeDecision'
import { fetchRecentTradeReviews, fetchTradeReviewDetail, fetchTradeReviewReport, startSingleTradeReviewTask, startSymbolReviewTask } from '@/api/tradeReview'
import { fetchDailyPositionReviewDates, fetchDailyPositionReview, startDailyPositionReviewTask } from '@/api/dailyPositionReview'
import { fetchRiskAssessmentHealth, fetchRecentRiskAssessments, fetchRiskAssessmentDetail, triggerRiskAssessment } from '@/api/riskAssessment'
import type { TradeDecisionHealth, TradeDecisionResult } from '@/types/tradeDecision'
import type { TradeReviewResult } from '@/types/tradeReview'
import type { DailyPositionReviewResult } from '@/types/dailyPositionReview'
import type { RiskAssessmentResult } from '@/types/riskAssessment'

type MainTab = 'decision' | 'reviewHub' | 'risk'
type ReviewSubTab = 'symbolReview' | 'singleReview' | 'dailyReview'

export default function TradeDecisionAgentView() {
  const { t, i18n } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [activeTab, setActiveTab] = useState<MainTab>('decision')
  const [reviewSubTab, setReviewSubTab] = useState<ReviewSubTab>('symbolReview')

  // Health
  const [health, setHealth] = useState<TradeDecisionHealth | null>(null)

  // Trade decision state
  const [decisions, setDecisions] = useState<TradeDecisionResult[]>([])
  const [selectedDecision, setSelectedDecision] = useState<TradeDecisionResult | null>(null)
  const [symbol, setSymbol] = useState('')
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<'entry' | 'holding'>('entry')
  const [generating, setGenerating] = useState(false)
  const [reportContent, setReportContent] = useState('')
  const [reportLoading, setReportLoading] = useState(false)
  const [viewMode, setViewMode] = useState<'structured' | 'report'>('report')

  // Trade review state (symbol + single)
  const [reviews, setReviews] = useState<TradeReviewResult[]>([])
  const [selectedReview, setSelectedReview] = useState<TradeReviewResult | null>(null)
  const [reviewSymbol, setReviewSymbol] = useState('')
  const [tradeId, setTradeId] = useState('')
  const [reviewGenerating, setReviewGenerating] = useState(false)
  const [reviewReport, setReviewReport] = useState('')
  const [reviewReportLoading, setReviewReportLoading] = useState(false)
  const [reviewViewMode, setReviewViewMode] = useState<'structured' | 'report'>('report')

  // Daily review state
  const [dates, setDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [dailyReview, setDailyReview] = useState<DailyPositionReviewResult | null>(null)
  const [dailyGenerating, setDailyGenerating] = useState(false)

  // Risk assessment state
  const [riskAssessments, setRiskAssessments] = useState<RiskAssessmentResult[]>([])
  const [selectedRisk, setSelectedRisk] = useState<RiskAssessmentResult | null>(null)
  const [riskQuestion, setRiskQuestion] = useState('')
  const [riskGenerating, setRiskGenerating] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const [h, d, r, datesData, ra] = await Promise.all([
        fetchTradeDecisionHealth(),
        fetchRecentTradeDecisions({ limit: 20 }),
        fetchRecentTradeReviews({ limit: 20 }),
        fetchDailyPositionReviewDates(),
        fetchRecentRiskAssessments(20),
      ])
      setHealth(h)
      setDecisions(d)
      setReviews(r)
      setDates(datesData)
      setRiskAssessments(ra)
      if (datesData.length > 0) {
        setSelectedDate(datesData[0])
        setDailyReview(await fetchDailyPositionReview(datesData[0]))
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeDecision.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { void loadData() }, [loadData])

  // --- Trade decision ---
  async function handleAnalyze() {
    if (!symbol.trim()) return
    setGenerating(true)
    setErrorMessage('')
    try {
      const fn = mode === 'entry' ? analyzeEntryDecision : analyzeHoldingDecision
      const result = await fn({ symbol: symbol.trim(), question: question.trim() || undefined })
      setSelectedDecision(result)
      setDecisions((prev) => [result, ...prev.filter((d) => d.id !== result.id)])
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeDecision.analysisFailed'))
    } finally {
      setGenerating(false)
    }
  }

  async function handleSelectDecision(id: string) {
    try {
      setSelectedDecision(await fetchTradeDecisionDetail(id))
      setReportLoading(true)
      const lang = i18n.language?.startsWith('zh') ? 'zh' : 'en'
      fetchTradeDecisionReport(id, lang)
        .then((r) => setReportContent(r.report))
        .catch(() => setReportContent(''))
        .finally(() => setReportLoading(false))
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeDecision.failedToLoadDecision'))
    }
  }

  // --- Trade review ---
  async function handleSymbolReview() {
    if (!reviewSymbol.trim()) return
    setReviewGenerating(true)
    setErrorMessage('')
    try {
      const result = await startSymbolReviewTask({ symbol: reviewSymbol.trim() })
      setSelectedReview(result)
      setReviews((prev) => [result, ...prev.filter((r) => r.id !== result.id)])
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeReview.reviewFailed'))
    } finally {
      setReviewGenerating(false)
    }
  }

  async function handleSingleReview() {
    if (!tradeId.trim() || !reviewSymbol.trim()) return
    setReviewGenerating(true)
    setErrorMessage('')
    try {
      const result = await startSingleTradeReviewTask(tradeId.trim(), reviewSymbol.trim())
      setSelectedReview(result)
      setReviews((prev) => [result, ...prev.filter((r) => r.id !== result.id)])
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeReview.reviewFailed'))
    } finally {
      setReviewGenerating(false)
    }
  }

  async function handleSelectReview(id: string) {
    try {
      setSelectedReview(await fetchTradeReviewDetail(id))
      setReviewReportLoading(true)
      const lang = i18n.language?.startsWith('zh') ? 'zh' : 'en'
      fetchTradeReviewReport(id, lang)
        .then((r) => setReviewReport(r.report))
        .catch(() => setReviewReport(''))
        .finally(() => setReviewReportLoading(false))
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeReview.failedToLoadReview'))
    }
  }

  // --- Daily review ---
  async function handleSelectDate(date: string) {
    setSelectedDate(date)
    setErrorMessage('')
    try {
      setDailyReview(await fetchDailyPositionReview(date))
    } catch {
      setDailyReview(null)
    }
  }

  async function handleDailyGenerate() {
    const date = selectedDate || new Date().toISOString().split('T')[0]
    setDailyGenerating(true)
    setErrorMessage('')
    try {
      const result = await startDailyPositionReviewTask(date)
      setDailyReview(result)
      if (!dates.includes(date)) setDates((prev) => [date, ...prev])
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('dailyReview.generationFailed'))
    } finally {
      setDailyGenerating(false)
    }
  }

  // --- Risk assessment ---
  async function handleRiskAssess() {
    setRiskGenerating(true)
    setErrorMessage('')
    try {
      const result = await triggerRiskAssessment(riskQuestion.trim() || undefined)
      setSelectedRisk(result)
      setRiskAssessments((prev) => [result, ...prev.filter((r) => r.id !== result.id)])
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeDecision.analysisFailed'))
    } finally {
      setRiskGenerating(false)
    }
  }

  async function handleSelectRisk(id: string) {
    try {
      setSelectedRisk(await fetchRiskAssessmentDetail(id))
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeDecision.failedToLoadDecision'))
    }
  }

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">{t('common.loading')}</div></div></section>
  }

  const decisionData = selectedDecision ?? null
  const reviewData = selectedReview ?? null
  const riskData = selectedRisk?.risk_report ?? null

  const actionLabels: Record<string, string> = {
    add: t('tradeDecision.actionAdd'), hold: t('tradeDecision.actionHold'),
    reduce: t('tradeDecision.actionReduce'), sell: t('tradeDecision.actionSell'),
    wait: t('tradeDecision.actionWait'), avoid: t('tradeDecision.actionAvoid'),
    watchlist: t('tradeDecision.actionWatchlist'),
  }

  const riskLevelColor: Record<string, string> = {
    low: 'var(--color-positive)', moderate: 'var(--color-accent)',
    high: '#ffb454', extreme: 'var(--color-negative)',
  }

  const TABS: { key: MainTab; label: string }[] = [
    { key: 'decision', label: t('tradeDecision.title') },
    { key: 'reviewHub', label: t('tradeDecision.reviewHub') },
    { key: 'risk', label: t('tradeDecision.riskAssessment') },
  ]

  const REVIEW_SUB_TABS: { key: ReviewSubTab; label: string }[] = [
    { key: 'symbolReview', label: t('tradeReview.symbolReview') },
    { key: 'singleReview', label: t('tradeReview.singleTradeReview') },
    { key: 'dailyReview', label: t('tradeReview.dailyReview') },
  ]

  return (
    <section className="page-section">
      {/* Header */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{t('tradeDecision.aiAgent')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('tradeDecision.title')}</h2>
              <p className="panel-subtitle">{t('tradeDecision.subtitle')}</p>
            </div>
            {health && (
              <span className={`tag ${health.llm_configured ? 'tag--positive' : 'tag--negative'}`}>
                {health.llm_configured ? t('tradeDecision.llmReady') : t('tradeDecision.llmMissing')}
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
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
        {TABS.map((tab) => (
          <button key={tab.key} className={`btn btn--sm ${activeTab === tab.key ? 'is-active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
            style={{
              borderRadius: 'var(--radius-sm)',
              background: activeTab === tab.key ? 'rgba(212,168,67,0.08)' : 'transparent',
              borderColor: activeTab === tab.key ? 'rgba(212,168,67,0.2)' : 'transparent',
              color: activeTab === tab.key ? 'var(--color-accent-strong)' : 'var(--color-text-secondary)',
            }}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* ============ Decision Input + Content ============ */}

      {activeTab === 'decision' && (
        <>
          <section className="surface-panel">
            <div className="surface-panel__content">
              <p className="eyebrow">{t('tradeDecision.analysisInput')}</p>
              <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
                <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
                  {(['entry', 'holding'] as const).map((m) => (
                    <button key={m} className={`btn btn--sm ${mode === m ? 'is-active' : ''}`}
                      onClick={() => setMode(m)}
                      style={{ borderRadius: 'var(--radius-sm)', background: mode === m ? 'rgba(212,168,67,0.08)' : 'transparent', borderColor: mode === m ? 'rgba(212,168,67,0.2)' : 'transparent', color: mode === m ? 'var(--color-accent-strong)' : 'var(--color-text-secondary)' }}>
                      {m === 'entry' ? t('tradeDecision.entryDecision') : t('tradeDecision.holdingDecision')}
                    </button>
                  ))}
                </div>
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                  <label className="field-stack" style={{ flex: 1 }}>
                    <span className="field-stack__label">{t('tradeDecision.symbol')}</span>
                    <input className="input" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder={t('tradeDecision.symbolPlaceholder')} />
                  </label>
                  <label className="field-stack" style={{ flex: 2 }}>
                    <span className="field-stack__label">{t('tradeDecision.question')}</span>
                    <input className="input" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder={t('tradeDecision.questionPlaceholder')} />
                  </label>
                  <button className="btn btn--accent" onClick={handleAnalyze} disabled={generating || !symbol.trim()}>
                    {generating ? t('tradeDecision.analyzing') : t('tradeDecision.analyze')}
                  </button>
                </div>
              </div>
            </div>
          </section>

          <div className="list-detail-layout">
            <section className="surface-panel">
              <div className="surface-panel__content" style={{ padding: '16px' }}>
                <p className="eyebrow" style={{ marginBottom: 8 }}>{t('tradeDecision.recentDecisions')} ({decisions.length})</p>
                <div style={{ display: 'grid', gap: 6, maxHeight: 400, overflow: 'auto' }}>
                  {decisions.length === 0 ? <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{t('tradeDecision.noDecisions')}</p> :
                    decisions.map((d) => (
                      <button key={d.id} className="btn btn--ghost btn--sm" onClick={() => handleSelectDecision(d.id)}
                        style={{ justifyContent: 'flex-start', textAlign: 'left', borderRadius: 'var(--radius-sm)', background: selectedDecision?.id === d.id ? 'rgba(212,168,67,0.08)' : 'transparent', borderColor: selectedDecision?.id === d.id ? 'rgba(212,168,67,0.2)' : 'transparent' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.85rem' }}>{d.symbol}</span>
                        <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{d.decision_type}</span>
                      </button>
                    ))
                  }
                </div>
              </div>
            </section>
            <section className="surface-panel">
              <div className="surface-panel__content">
                {!selectedDecision ? <div className="empty-state" style={{ minHeight: 300 }}>{t('tradeDecision.selectOrRun')}</div> :
                 !decisionData ? <div className="empty-state" style={{ minHeight: 300 }}>{t('tradeDecision.decisionDataParseError')}</div> : (
                  <div style={{ display: 'grid', gap: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                        <p className="eyebrow" style={{ margin: 0 }}>{selectedDecision.symbol}</p>
                        <span className="tag tag--accent">{selectedDecision.decision_type}</span>
                        {decisionData.action && <span className="tag tag--positive">{actionLabels[decisionData.action] ?? decisionData.action}</span>}
                        {decisionData.confidence && <span className="tag">{decisionData.confidence}</span>}
                        {decisionData.overall_score != null && decisionData.overall_score > 0 && <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 700, color: 'var(--color-accent-strong)' }}>{decisionData.overall_score}/100</span>}
                      </div>
                      <div style={{ display: 'flex', gap: 4 }}>
                        <button className={`btn btn--sm ${viewMode === 'report' ? 'btn--accent' : ''}`} onClick={() => setViewMode('report')}>{t('tradeDecision.reportView')}</button>
                        <button className={`btn btn--sm ${viewMode === 'structured' ? 'btn--accent' : ''}`} onClick={() => setViewMode('structured')}>{t('tradeDecision.structuredView')}</button>
                      </div>
                    </div>
                    {viewMode === 'report' && <ReportView loading={reportLoading} content={reportContent} emptyText={t('tradeDecision.noReportAvailable')} />}
                    {viewMode === 'structured' && (
                      <div style={{ display: 'grid', gap: 16 }}>
                        {decisionData.decision_summary && <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>{decisionData.decision_summary}</p>}
                        <BulletList label={t('tradeDecision.keyReasons')} items={decisionData.key_reasons} color="var(--color-text-secondary)" />
                        <BulletList label={t('tradeDecision.risks')} items={decisionData.major_risks} color="var(--color-negative)" labelColor="var(--color-negative)" />
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>
          </div>
        </>
      )}

      {/* ============ Review Hub ============ */}

      {activeTab === 'reviewHub' && (
        <>
          {/* Sub-tabs */}
          <div style={{ display: 'flex', gap: 4 }}>
            {REVIEW_SUB_TABS.map((tab) => (
              <button key={tab.key} className={`btn btn--sm ${reviewSubTab === tab.key ? 'is-active' : ''}`}
                onClick={() => setReviewSubTab(tab.key)}
                style={{
                  borderRadius: 'var(--radius-sm)',
                  background: reviewSubTab === tab.key ? 'rgba(212,168,67,0.08)' : 'transparent',
                  borderColor: reviewSubTab === tab.key ? 'rgba(212,168,67,0.2)' : 'transparent',
                  color: reviewSubTab === tab.key ? 'var(--color-accent-strong)' : 'var(--color-text-secondary)',
                  fontSize: '0.8rem',
                }}>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Input forms */}
          <section className="surface-panel">
            <div className="surface-panel__content">
              {reviewSubTab === 'symbolReview' && (
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                  <label className="field-stack" style={{ flex: 1 }}>
                    <span className="field-stack__label">{t('tradeReview.symbol')}</span>
                    <input className="input" value={reviewSymbol} onChange={(e) => setReviewSymbol(e.target.value.toUpperCase())} placeholder={t('tradeDecision.reviewSymbolPlaceholder')} />
                  </label>
                  <button className="btn btn--accent" onClick={handleSymbolReview} disabled={reviewGenerating || !reviewSymbol.trim()}>
                    {reviewGenerating ? t('tradeReview.generating') : t('tradeReview.generateReview')}
                  </button>
                </div>
              )}
              {reviewSubTab === 'singleReview' && (
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                  <label className="field-stack" style={{ flex: 1 }}>
                    <span className="field-stack__label">{t('tradeReview.symbol')}</span>
                    <input className="input" value={reviewSymbol} onChange={(e) => setReviewSymbol(e.target.value.toUpperCase())} placeholder={t('tradeDecision.reviewSymbolPlaceholder')} />
                  </label>
                  <label className="field-stack" style={{ flex: 1 }}>
                    <span className="field-stack__label">{t('tradeReview.tradeId')}</span>
                    <input className="input" value={tradeId} onChange={(e) => setTradeId(e.target.value)} placeholder={t('tradeDecision.tradeIdPlaceholder')} />
                  </label>
                  <button className="btn btn--accent" onClick={handleSingleReview} disabled={reviewGenerating || !reviewSymbol.trim() || !tradeId.trim()}>
                    {reviewGenerating ? t('tradeReview.generating') : t('tradeReview.generateReview')}
                  </button>
                </div>
              )}
              {reviewSubTab === 'dailyReview' && (
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                  <label className="field-stack" style={{ flex: 1 }}>
                    <span className="field-stack__label">{t('dailyReview.reportDate')}</span>
                    <select className="select" value={selectedDate} onChange={(e) => handleSelectDate(e.target.value)}>
                      <option value="">{t('dailyReview.selectDate')}</option>
                      {dates.map((d) => <option key={d} value={d}>{d}</option>)}
                    </select>
                  </label>
                  <button className="btn btn--accent" onClick={handleDailyGenerate} disabled={dailyGenerating}>
                    {dailyGenerating ? t('dailyReview.generating') : t('dailyReview.generateReview')}
                  </button>
                </div>
              )}
            </div>
          </section>

          {/* Review content: symbol / single share list+detail layout */}
          {(reviewSubTab === 'symbolReview' || reviewSubTab === 'singleReview') && (
            <div className="list-detail-layout">
              <section className="surface-panel">
                <div className="surface-panel__content" style={{ padding: '16px' }}>
                  <p className="eyebrow" style={{ marginBottom: 8 }}>{t('tradeReview.recentReviews')} ({reviews.length})</p>
                  <div style={{ display: 'grid', gap: 6, maxHeight: 400, overflow: 'auto' }}>
                    {reviews.length === 0 ? <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{t('tradeReview.noReviews')}</p> :
                      reviews.map((r) => (
                        <button key={r.id} className="btn btn--ghost btn--sm" onClick={() => handleSelectReview(r.id)}
                          style={{ justifyContent: 'flex-start', textAlign: 'left', borderRadius: 'var(--radius-sm)', background: selectedReview?.id === r.id ? 'rgba(212,168,67,0.08)' : 'transparent', borderColor: selectedReview?.id === r.id ? 'rgba(212,168,67,0.2)' : 'transparent' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.85rem' }}>{r.symbol || r.review_type}</span>
                          <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{r.review_type}</span>
                        </button>
                      ))
                    }
                  </div>
                </div>
              </section>
              <section className="surface-panel">
                <div className="surface-panel__content">
                  {!selectedReview ? <div className="empty-state" style={{ minHeight: 300 }}>{t('tradeReview.selectOrGenerate')}</div> :
                   !reviewData ? <div className="empty-state" style={{ minHeight: 300 }}>{t('tradeReview.reviewDataParseError')}</div> : (
                    <div style={{ display: 'grid', gap: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                          <p className="eyebrow" style={{ margin: 0 }}>{selectedReview.symbol || selectedReview.review_type}</p>
                          {reviewData.overall_score != null && <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 700, color: 'var(--color-accent-strong)' }}>{reviewData.overall_score}/100</span>}
                          {reviewData.rating && <span className={`tag ${reviewData.rating === 'excellent' ? 'tag--positive' : reviewData.rating === 'poor' ? 'tag--negative' : ''}`}>{reviewData.rating}</span>}
                        </div>
                        <div style={{ display: 'flex', gap: 4 }}>
                          <button className={`btn btn--sm ${reviewViewMode === 'report' ? 'btn--accent' : ''}`} onClick={() => setReviewViewMode('report')}>{t('tradeReview.reportView')}</button>
                          <button className={`btn btn--sm ${reviewViewMode === 'structured' ? 'btn--accent' : ''}`} onClick={() => setReviewViewMode('structured')}>{t('tradeReview.structuredView')}</button>
                        </div>
                      </div>
                      {reviewViewMode === 'report' && <ReportView loading={reviewReportLoading} content={reviewReport} emptyText={t('tradeReview.noReportAvailable')} />}
                      {reviewViewMode === 'structured' && (
                        <div style={{ display: 'grid', gap: 16 }}>
                          {reviewData.summary && <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>{reviewData.summary}</p>}
                          <BulletList label={t('tradeReview.strengths')} items={reviewData.strengths} color="var(--color-positive)" labelColor="var(--color-positive)" />
                          <BulletList label={t('tradeReview.weaknesses')} items={reviewData.weaknesses} color="var(--color-negative)" labelColor="var(--color-negative)" />
                          <BulletList label={t('tradeReview.improvements')} items={reviewData.improvement_suggestions} />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </section>
            </div>
          )}

          {/* Daily review content */}
          {reviewSubTab === 'dailyReview' && (
            <section className="surface-panel">
              <div className="surface-panel__content">
                {!dailyReview ? <div className="empty-state" style={{ minHeight: 300 }}>{t('dailyReview.selectOrGenerate')}</div> : (
                  <div style={{ display: 'grid', gap: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                      <p className="eyebrow" style={{ margin: 0 }}>{t('dailyReview.dailyReviewLabel')}</p>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>{dailyReview.report_date}</span>
                    </div>
                    {dailyReview.summary && <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>{dailyReview.summary}</p>}
                    {dailyReview.account_conclusion && <div><p className="eyebrow">{t('dailyReview.accountConclusion')}</p><p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: '0.88rem', lineHeight: 1.6 }}>{dailyReview.account_conclusion}</p></div>}
                    {dailyReview.attribution_summary && <div><p className="eyebrow">{t('dailyReview.attribution')}</p><p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: '0.88rem', lineHeight: 1.6 }}>{dailyReview.attribution_summary}</p></div>}
                    {dailyReview.focus_symbol_analyses?.length > 0 && (
                      <div>
                        <p className="eyebrow">{t('dailyReview.focusSymbols')}</p>
                        <div style={{ display: 'grid', gap: 8, marginTop: 4 }}>
                          {dailyReview.focus_symbol_analyses.map((s: Record<string, unknown>, i: number) => (
                            <div key={i} style={{ padding: '10px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(10,14,26,0.4)', border: '1px solid var(--color-border-subtle)' }}>
                              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-text-bright)' }}>{String(s.symbol ?? '')}</span>
                              <p style={{ margin: '4px 0 0', color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>{String(s.analysis ?? s.summary ?? '')}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {dailyReview.tomorrow_watchlist?.length > 0 && (
                      <div>
                        <p className="eyebrow">{t('dailyReview.watchlist')}</p>
                        <ul style={{ margin: '4px 0 0', padding: '0 0 0 16px', color: 'var(--color-text-secondary)', fontSize: '0.88rem' }}>
                          {dailyReview.tomorrow_watchlist.map((w: string | Record<string, unknown>, i: number) => <li key={i}>{typeof w === 'string' ? w : JSON.stringify(w)}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>
          )}
        </>
      )}

      {/* ============ Risk Assessment ============ */}

      {activeTab === 'risk' && (
        <>
          <section className="surface-panel">
            <div className="surface-panel__content">
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
                <label className="field-stack" style={{ flex: 1 }}>
                  <span className="field-stack__label">{t('tradeDecision.question')}</span>
                  <input className="input" value={riskQuestion} onChange={(e) => setRiskQuestion(e.target.value)} placeholder={t('tradeDecision.riskQuestionPlaceholder')} />
                </label>
                <button className="btn btn--accent" onClick={handleRiskAssess} disabled={riskGenerating}>
                  {riskGenerating ? t('tradeDecision.analyzing') : t('tradeDecision.riskAssess')}
                </button>
              </div>
            </div>
          </section>

          <div className="list-detail-layout">
            <section className="surface-panel">
              <div className="surface-panel__content" style={{ padding: '16px' }}>
                <p className="eyebrow" style={{ marginBottom: 8 }}>{t('tradeDecision.recentAssessments')} ({riskAssessments.length})</p>
                <div style={{ display: 'grid', gap: 6, maxHeight: 400, overflow: 'auto' }}>
                  {riskAssessments.length === 0 ? <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{t('tradeDecision.noAssessments')}</p> :
                    riskAssessments.map((r) => {
                      const report = r.risk_report
                      return (
                        <button key={r.id} className="btn btn--ghost btn--sm" onClick={() => handleSelectRisk(r.id)}
                          style={{ justifyContent: 'flex-start', textAlign: 'left', borderRadius: 'var(--radius-sm)', background: selectedRisk?.id === r.id ? 'rgba(212,168,67,0.08)' : 'transparent', borderColor: selectedRisk?.id === r.id ? 'rgba(212,168,67,0.2)' : 'transparent' }}>
                          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.85rem' }}>{r.assessment_type}</span>
                          {report && typeof report === 'object' && <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: riskLevelColor[report.risk_level] || 'var(--color-text-muted)' }}>{report.risk_level} {report.overall_risk_score}/25</span>}
                        </button>
                      )
                    })
                  }
                </div>
              </div>
            </section>
            <section className="surface-panel">
              <div className="surface-panel__content">
                {!selectedRisk ? <div className="empty-state" style={{ minHeight: 300 }}>{t('tradeDecision.selectOrRunRisk')}</div> :
                 !riskData ? <div className="empty-state" style={{ minHeight: 300 }}>{t('tradeDecision.decisionDataParseError')}</div> : (
                  <div style={{ display: 'grid', gap: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                      <p className="eyebrow" style={{ margin: 0 }}>{t('tradeDecision.riskAssessment')}</p>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.4rem', fontWeight: 700, color: riskLevelColor[riskData.risk_level] || 'var(--color-text-bright)' }}>{riskData.overall_risk_score}/25</span>
                      <span className="tag" style={{ background: `${riskLevelColor[riskData.risk_level]}20`, color: riskLevelColor[riskData.risk_level] }}>{riskData.risk_level?.toUpperCase()}</span>
                    </div>
                    {riskData.summary && <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>{riskData.summary}</p>}
                    {riskData.concentration_risk && <RiskDimensionCard title={t('tradeDecision.concentrationRisk')} dim={riskData.concentration_risk} />}
                    {riskData.sector_exposure && <RiskDimensionCard title={t('tradeDecision.sectorExposure')} dim={riskData.sector_exposure} />}
                    {riskData.liquidity_risk && (
                      <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(10,14,26,0.4)', border: '1px solid var(--color-border-subtle)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                          <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{t('tradeDecision.liquidityRisk')}</span>
                          <span className="tag" style={{ fontSize: '0.7rem', color: riskLevelColor[riskData.liquidity_risk.risk_level] }}>{riskData.liquidity_risk.risk_level}</span>
                        </div>
                        <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', margin: 0 }}>Cash: {(riskData.liquidity_risk.cash_pct * 100).toFixed(1)}% · Deployable: ${riskData.liquidity_risk.deployable_liquidity?.toLocaleString()}</p>
                      </div>
                    )}
                    {riskData.stress_test && <RiskDimensionCard title={t('tradeDecision.stressTest')} dim={riskData.stress_test} />}
                    <BulletList label={t('tradeDecision.keyRisks')} items={riskData.key_risks} color="var(--color-negative)" labelColor="var(--color-negative)" />
                    <BulletList label={t('tradeDecision.recommendations')} items={riskData.recommendations} color="var(--color-positive)" labelColor="var(--color-positive)" />
                    <BulletList label={t('tradeDecision.watchPoints')} items={riskData.watch_points} />
                  </div>
                )}
              </div>
            </section>
          </div>
        </>
      )}
    </section>
  )
}

/* ---------- Shared components ---------- */

function ReportView({ loading, content, emptyText }: { loading: boolean; content: string; emptyText: string }) {
  const { t } = useTranslation()
  return (
    <div className="copilot-markdown" style={{ lineHeight: 1.7 }}>
      {loading ? <p style={{ color: 'var(--color-text-muted)' }}>{t('common.loading')}</p> :
       content ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown> :
       <p style={{ color: 'var(--color-text-muted)' }}>{emptyText}</p>}
    </div>
  )
}

function BulletList({ label, items, color, labelColor }: { label: string; items?: string[]; color?: string; labelColor?: string }) {
  if (!items?.length) return null
  return (
    <div>
      <p className="eyebrow" style={labelColor ? { color: labelColor } : undefined}>{label}</p>
      <ul style={{ margin: '4px 0 0', padding: '0 0 0 16px', color: color || 'var(--color-text-secondary)', fontSize: '0.88rem' }}>
        {items.map((item, i) => <li key={i} style={{ marginBottom: 4 }}>{item}</li>)}
      </ul>
    </div>
  )
}

function RiskDimensionCard({ title, dim }: { title: string; dim: { score: number; max_score: number; risk_level: string; findings: string[] } }) {
  const color: Record<string, string> = {
    low: 'var(--color-positive)', moderate: 'var(--color-accent)',
    high: '#ffb454', extreme: 'var(--color-negative)',
  }
  return (
    <div style={{ padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'rgba(10,14,26,0.4)', border: '1px solid var(--color-border-subtle)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{title}</span>
        <span className="tag" style={{ fontSize: '0.7rem', color: color[dim.risk_level] }}>{dim.risk_level}</span>
        <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{dim.score}/{dim.max_score}</span>
      </div>
      {dim.findings?.length > 0 && (
        <ul style={{ margin: 0, padding: '0 0 0 14px', fontSize: '0.8rem', color: 'var(--color-text-secondary)' }}>
          {dim.findings.map((f: string, i: number) => <li key={i}>{f}</li>)}
        </ul>
      )}
    </div>
  )
}
