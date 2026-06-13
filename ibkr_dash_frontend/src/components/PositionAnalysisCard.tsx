import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { fetchLatestPositionAnalysis, type PositionAnalysisResult } from '@/api/positionAnalysis'

export default function PositionAnalysisCard() {
  const { t, i18n } = useTranslation()
  const [analysis, setAnalysis] = useState<PositionAnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    const lang = i18n.language?.startsWith('zh') ? 'zh' : 'en'
    setLoading(true)
    fetchLatestPositionAnalysis(lang)
      .then((res) => { if (!cancelled) setAnalysis(res) })
      .catch(() => { /* no analysis available, hide card */ })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [i18n.language])

  // Don't show if loading, no data, or LLM not configured
  if (loading || !analysis?.report) return null

  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso)
      return d.toLocaleString(i18n.language?.startsWith('zh') ? 'zh-CN' : 'en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
      })
    } catch {
      return iso
    }
  }

  return (
    <section className="surface-panel">
      <div className="surface-panel__content">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
            <p className="eyebrow" style={{ margin: 0 }}>{t('positions.aiAnalysis')}</p>
            <span style={{
              fontFamily: 'var(--font-mono)',
              fontSize: '0.65rem',
              color: 'var(--color-text-muted)',
            }}>
              {formatDate(analysis.created_at)}
            </span>
          </div>
          <span className="tag tag--accent">{analysis.report_date}</span>
        </div>
        <div className="copilot-markdown" style={{ lineHeight: 1.65 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{analysis.report}</ReactMarkdown>
        </div>
      </div>
    </section>
  )
}
