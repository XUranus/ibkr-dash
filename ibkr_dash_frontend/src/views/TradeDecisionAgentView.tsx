import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { analyzeEntryDecision, analyzeHoldingDecision, fetchRecentTradeDecisions, fetchTradeDecisionDetail, fetchTradeDecisionHealth } from '@/api/tradeDecision'
import type { TradeDecisionHealth, TradeDecisionResult } from '@/types/tradeDecision'

type DecisionMode = 'entry' | 'holding'

export default function TradeDecisionAgentView() {
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [health, setHealth] = useState<TradeDecisionHealth | null>(null)
  const [decisions, setDecisions] = useState<TradeDecisionResult[]>([])
  const [selectedDecision, setSelectedDecision] = useState<TradeDecisionResult | null>(null)
  const [symbol, setSymbol] = useState('')
  const [question, setQuestion] = useState('')
  const [mode, setMode] = useState<DecisionMode>('entry')
  const [generating, setGenerating] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const [h, d] = await Promise.all([fetchTradeDecisionHealth(), fetchRecentTradeDecisions({ limit: 20 })])
      setHealth(h)
      setDecisions(d)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeDecision.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

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
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : t('tradeDecision.failedToLoadDecision'))
    }
  }

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">{t('common.loading')}</div></div></section>
  }

  const decisionData = selectedDecision ?? null

  const actionLabels: Record<string, string> = {
    add: t('tradeDecision.actionAdd'),
    hold: t('tradeDecision.actionHold'),
    reduce: t('tradeDecision.actionReduce'),
    sell: t('tradeDecision.actionSell'),
    wait: t('tradeDecision.actionWait'),
    avoid: t('tradeDecision.actionAvoid'),
    watchlist: t('tradeDecision.actionWatchlist'),
  }

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

      {/* Input Form */}
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.1s both' }}>
        <div className="surface-panel__content">
          <p className="eyebrow">{t('tradeDecision.analysisInput')}</p>
          <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>
            <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
              {(['entry', 'holding'] as const).map((m) => (
                <button key={m} className={`btn btn--sm ${mode === m ? 'is-active' : ''}`}
                  onClick={() => setMode(m)}
                  style={{
                    borderRadius: 'var(--radius-sm)',
                    background: mode === m ? 'rgba(212,168,67,0.08)' : 'transparent',
                    borderColor: mode === m ? 'rgba(212,168,67,0.2)' : 'transparent',
                    color: mode === m ? 'var(--color-accent-strong)' : 'var(--color-text-secondary)',
                  }}>
                  {m === 'entry' ? t('tradeDecision.entryDecision') : t('tradeDecision.holdingDecision')}
                </button>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
              <label className="field-stack" style={{ flex: 1 }}>
                <span className="field-stack__label">{t('tradeDecision.symbol')}</span>
                <input className="input" value={symbol} onChange={(e) => setSymbol(e.target.value.toUpperCase())} placeholder="AAPL" />
              </label>
              <label className="field-stack" style={{ flex: 2 }}>
                <span className="field-stack__label">{t('tradeDecision.question')}</span>
                <input className="input" value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Should I add to my AAPL position?" />
              </label>
              <button className="btn btn--accent" onClick={handleAnalyze} disabled={generating || !symbol.trim()}>
                {generating ? t('tradeDecision.analyzing') : t('tradeDecision.analyze')}
              </button>
            </div>
          </div>
        </div>
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 'var(--space-4)' }}>
        {/* Recent decisions list */}
        <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.2s both' }}>
          <div className="surface-panel__content" style={{ padding: '16px' }}>
            <p className="eyebrow" style={{ marginBottom: 8 }}>{t('tradeDecision.recentDecisions')} ({decisions.length})</p>
            <div style={{ display: 'grid', gap: 6, maxHeight: 400, overflow: 'auto' }}>
              {decisions.length === 0 ? (
                <p style={{ color: 'var(--color-text-muted)', fontSize: '0.85rem' }}>{t('tradeDecision.noDecisions')}</p>
              ) : (
                decisions.map((d) => (
                  <button key={d.id} className="btn btn--ghost btn--sm"
                    onClick={() => handleSelectDecision(d.id)}
                    style={{
                      justifyContent: 'flex-start', textAlign: 'left',
                      borderRadius: 'var(--radius-sm)',
                      background: selectedDecision?.id === d.id ? 'rgba(212,168,67,0.08)' : 'transparent',
                      borderColor: selectedDecision?.id === d.id ? 'rgba(212,168,67,0.2)' : 'transparent',
                    }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.85rem' }}>{d.symbol}</span>
                    <span style={{ marginLeft: 'auto', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{d.decision_type}</span>
                  </button>
                ))
              )}
            </div>
          </div>
        </section>

        {/* Decision detail */}
        <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease 0.3s both' }}>
          <div className="surface-panel__content">
            {!selectedDecision ? (
              <div className="empty-state" style={{ minHeight: 300 }}>{t('tradeDecision.selectOrRun')}</div>
            ) : !decisionData ? (
              <div className="empty-state" style={{ minHeight: 300 }}>{t('tradeDecision.decisionDataParseError')}</div>
            ) : (
              <div style={{ display: 'grid', gap: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                  <p className="eyebrow" style={{ margin: 0 }}>{selectedDecision.symbol}</p>
                  <span className="tag tag--accent">{selectedDecision.decision_type}</span>
                  {decisionData.action && (
                    <span className="tag tag--positive">{actionLabels[decisionData.action] ?? decisionData.action}</span>
                  )}
                  {decisionData.confidence && (
                    <span className="tag">{decisionData.confidence}</span>
                  )}
                  {decisionData.overall_score != null && decisionData.overall_score > 0 && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '1.2rem', fontWeight: 700, color: 'var(--color-accent-strong)' }}>{decisionData.overall_score}/100</span>
                  )}
                </div>

                {decisionData.decision_summary && (
                  <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', lineHeight: 1.6 }}>{decisionData.decision_summary}</p>
                )}

                {decisionData.key_reasons?.length > 0 && (
                  <div>
                    <p className="eyebrow">{t('tradeDecision.keyReasons')}</p>
                    <ul style={{ margin: '4px 0 0', padding: '0 0 0 16px', color: 'var(--color-text-secondary)', fontSize: '0.88rem' }}>
                      {decisionData.key_reasons.map((r: string, i: number) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                )}

                {decisionData.major_risks?.length > 0 && (
                  <div>
                    <p className="eyebrow" style={{ color: 'var(--color-negative)' }}>{t('tradeDecision.risks')}</p>
                    <ul style={{ margin: '4px 0 0', padding: '0 0 0 16px', color: 'var(--color-text-secondary)', fontSize: '0.88rem' }}>
                      {decisionData.major_risks.map((r: string, i: number) => <li key={i}>{r}</li>)}
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
