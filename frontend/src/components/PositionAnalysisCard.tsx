import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { fetchLatestPositionAnalysis, type PositionAnalysisResult } from '@/api/positionAnalysis'

/** Parsed position analysis data from the JSON report */
interface ScoreDetail {
  score: number
  max_score: number
  reason: string
}

interface PositionAdvice {
  action: 'add' | 'hold' | 'reduce' | 'close'
  target_pct: number
  max_pct: number
  rationale: string
  urgency: 'high' | 'medium' | 'low'
}

interface ParsedAnalysis {
  overall_score: number
  rating: 'excellent' | 'good' | 'fair' | 'poor'
  summary: string
  score_detail: Record<string, ScoreDetail>
  position_advice: PositionAdvice
  strengths: string[]
  weaknesses: string[]
  key_risks: string[]
}

const RATING_LABELS: Record<string, { zh: string; en: string; color: string }> = {
  excellent: { zh: '优秀', en: 'Excellent', color: '#10b981' },
  good: { zh: '良好', en: 'Good', color: '#56d5ff' },
  fair: { zh: '一般', en: 'Fair', color: '#ffb454' },
  poor: { zh: '较差', en: 'Poor', color: '#ff7b98' },
}

const ACTION_LABELS: Record<string, { zh: string; en: string; icon: string }> = {
  add: { zh: '加仓', en: 'Add', icon: '📈' },
  hold: { zh: '持有', en: 'Hold', icon: '✋' },
  reduce: { zh: '减仓', en: 'Reduce', icon: '📉' },
  close: { zh: '清仓', en: 'Close', icon: '🚫' },
}

const DIMENSION_LABELS: Record<string, { zh: string; en: string }> = {
  company_quality: { zh: '公司质量', en: 'Company Quality' },
  valuation_quality: { zh: '估值质量', en: 'Valuation' },
  trend_strength: { zh: '趋势强度', en: 'Trend Strength' },
  account_fit: { zh: '账户适配', en: 'Account Fit' },
  risk_reward: { zh: '风险收益', en: 'Risk/Reward' },
  review_constraints: { zh: '复盘约束', en: 'Constraints' },
  event_catalyst: { zh: '事件催化', en: 'Catalysts' },
}

function parseAnalysis(report: string): ParsedAnalysis | null {
  try {
    const data = JSON.parse(report)
    if (data && typeof data === 'object' && data.overall_score != null && data.score_detail) {
      return data as ParsedAnalysis
    }
    return null
  } catch {
    // Not JSON - it's Markdown format
    return null
  }
}

function ScoreBar({ score, maxScore }: { score: number; maxScore: number }) {
  const pct = maxScore > 0 ? (score / maxScore) * 100 : 0
  const color = pct >= 70 ? '#10b981' : pct >= 50 ? '#ffb454' : '#ff7b98'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, width: '100%' }}>
      <div style={{
        flex: 1, height: 6, borderRadius: 3,
        background: 'rgba(255,255,255,0.06)',
        overflow: 'hidden',
      }}>
        <div style={{
          width: `${pct}%`, height: '100%', borderRadius: 3,
          background: color,
          transition: 'width 0.3s ease',
        }} />
      </div>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '0.75rem',
        color: 'var(--color-text-secondary)', minWidth: 40, textAlign: 'right',
      }}>
        {score}/{maxScore}
      </span>
    </div>
  )
}

/** Structured view for JSON format */
function StructuredView({ parsed, lang }: { parsed: ParsedAnalysis; lang: 'zh' | 'en' }) {
  const ratingInfo = RATING_LABELS[parsed.rating] ?? RATING_LABELS.fair
  const adviceInfo = ACTION_LABELS[parsed.position_advice?.action] ?? ACTION_LABELS.hold

  return (
    <>
      {/* Overall Score + Rating */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 16,
        padding: '12px 16px', borderRadius: 'var(--radius-md)',
        background: 'rgba(255,255,255,0.03)', marginBottom: 16,
      }}>
        <div style={{
          fontSize: '2rem', fontWeight: 700,
          fontFamily: 'var(--font-mono)',
          color: ratingInfo.color,
          lineHeight: 1,
        }}>
          {parsed.overall_score}
        </div>
        <div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: ratingInfo.color }}>
            {ratingInfo[lang]}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
            /100
          </div>
        </div>
        {parsed.position_advice && (
          <div style={{
            marginLeft: 'auto', padding: '6px 12px', borderRadius: 'var(--radius-sm)',
            background: 'rgba(255,255,255,0.05)',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <span>{adviceInfo.icon}</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>
              {adviceInfo[lang]}
            </span>
            {parsed.position_advice.urgency === 'high' && (
              <span style={{ color: '#ff7b98', fontSize: '0.7rem' }}>●</span>
            )}
          </div>
        )}
      </div>

      {/* Summary */}
      <p style={{
        fontSize: '0.85rem', lineHeight: 1.6,
        color: 'var(--color-text-secondary)', margin: '0 0 16px',
      }}>
        {parsed.summary}
      </p>

      {/* Score Breakdown */}
      {parsed.score_detail && (
        <div style={{ marginBottom: 16 }}>
          <div style={{
            fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase',
            letterSpacing: '0.05em', color: 'var(--color-text-muted)', marginBottom: 8,
          }}>
            {lang === 'zh' ? '评分明细' : 'Score Breakdown'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Object.entries(parsed.score_detail).map(([key, detail]) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{
                  fontSize: '0.75rem', color: 'var(--color-text-secondary)',
                  minWidth: 70, textAlign: 'right',
                }}>
                  {DIMENSION_LABELS[key]?.[lang] ?? key}
                </span>
                <ScoreBar score={detail.score} maxScore={detail.max_score} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Advice Rationale */}
      {parsed.position_advice?.rationale && (
        <div style={{
          padding: '10px 12px', borderRadius: 'var(--radius-sm)',
          background: 'rgba(255,255,255,0.03)', marginBottom: 16,
          borderLeft: `3px solid ${ratingInfo.color}`,
        }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-muted)', marginBottom: 4 }}>
            {lang === 'zh' ? '💡 建议理由' : '💡 Rationale'}
          </div>
          <p style={{ fontSize: '0.8rem', lineHeight: 1.5, color: 'var(--color-text-secondary)', margin: 0 }}>
            {parsed.position_advice.rationale}
          </p>
        </div>
      )}

      {/* Strengths & Weaknesses */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
        {parsed.strengths?.length > 0 && (
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#10b981', marginBottom: 6 }}>
              ✅ {lang === 'zh' ? '优点' : 'Strengths'}
            </div>
            <ul style={{ margin: 0, paddingLeft: 16, fontSize: '0.78rem', lineHeight: 1.5, color: 'var(--color-text-secondary)' }}>
              {parsed.strengths.slice(0, 3).map((s, i) => <li key={i}>{s}</li>)}
            </ul>
          </div>
        )}
        {parsed.weaknesses?.length > 0 && (
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ffb454', marginBottom: 6 }}>
              ⚠️ {lang === 'zh' ? '风险点' : 'Weaknesses'}
            </div>
            <ul style={{ margin: 0, paddingLeft: 16, fontSize: '0.78rem', lineHeight: 1.5, color: 'var(--color-text-secondary)' }}>
              {parsed.weaknesses.slice(0, 3).map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}
      </div>

      {/* Key Risks */}
      {parsed.key_risks?.length > 0 && (
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ff7b98', marginBottom: 6 }}>
            🔴 {lang === 'zh' ? '关键风险' : 'Key Risks'}
          </div>
          <ul style={{ margin: 0, paddingLeft: 16, fontSize: '0.78rem', lineHeight: 1.5, color: 'var(--color-text-secondary)' }}>
            {parsed.key_risks.slice(0, 3).map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}
    </>
  )
}

export default function PositionAnalysisCard() {
  const { t, i18n } = useTranslation()
  const lang = i18n.language?.startsWith('zh') ? 'zh' : 'en'
  const [analysis, setAnalysis] = useState<PositionAnalysisResult | null>(null)
  const [parsed, setParsed] = useState<ParsedAnalysis | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchLatestPositionAnalysis(lang)
      .then((res) => {
        if (cancelled) return
        setAnalysis(res)
        // Try to parse as JSON first, fallback to null (will render as Markdown)
        const reportStr = typeof res.report === 'string' ? res.report : JSON.stringify(res.report)
        setParsed(parseAnalysis(reportStr))
      })
      .catch(() => { /* no analysis available */ })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [lang])

  if (loading || !analysis?.report) return null

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString(lang === 'zh' ? 'zh-CN' : 'en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    } catch {
      return iso
    }
  }

  const reportStr = typeof analysis.report === 'string' ? analysis.report : JSON.stringify(analysis.report)

  return (
    <section className="surface-panel">
      <div className="surface-panel__content">
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <p className="eyebrow" style={{ margin: 0 }}>{t('positions.aiAnalysis')}</p>
            <span style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.65rem',
              color: 'var(--color-text-muted)',
            }}>
              {formatDate(analysis.created_at)}
            </span>
          </div>
          <span className="tag tag--accent">{analysis.report_date}</span>
        </div>

        {/* Render based on format */}
        {parsed ? (
          <StructuredView parsed={parsed} lang={lang} />
        ) : (
          // Markdown format (legacy)
          <div className="copilot-markdown" style={{ lineHeight: 1.65 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{reportStr}</ReactMarkdown>
          </div>
        )}
      </div>
    </section>
  )
}
