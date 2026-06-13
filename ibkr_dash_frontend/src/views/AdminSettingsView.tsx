import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { fetchAllSettings, updateSettings, resetSettings, type SettingItem, type SettingsByCategory } from '@/api/adminSettings'
import AdminTabs from '@/components/AdminTabs'

const CATEGORY_LABELS: Record<string, { zh: string; en: string }> = {
  ibkr: { zh: 'IBKR 连接', en: 'IBKR Connection' },
  llm: { zh: 'AI / LLM', en: 'AI / LLM' },
  scheduler: { zh: '调度器', en: 'Scheduler' },
  auth: { zh: '认证', en: 'Authentication' },
  advanced: { zh: '高级', en: 'Advanced' },
}

export default function AdminSettingsView() {
  const { t, i18n } = useTranslation()
  const isZh = i18n.language?.startsWith('zh')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [noticeMessage, setNoticeMessage] = useState('')
  const [settings, setSettings] = useState<SettingsByCategory>({})
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [expandedCat, setExpandedCat] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setErrorMessage('')
    try {
      const data = await fetchAllSettings()
      setSettings(data)
      setExpandedCat(Object.keys(data)[0] || null)
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadData() }, [loadData])

  function handleEdit(key: string, value: string) {
    setEdits((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSave() {
    if (Object.keys(edits).length === 0) return
    setSaving(true)
    setErrorMessage('')
    setNoticeMessage('')
    try {
      await updateSettings(edits)
      setEdits({})
      setNoticeMessage(isZh ? '配置已保存' : 'Settings saved')
      await loadData()
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  async function handleReset(key: string) {
    if (!confirm(isZh ? `重置 ${key} 为默认值？` : `Reset ${key} to default?`)) return
    try {
      await resetSettings([key])
      setNoticeMessage(isZh ? `${key} 已重置` : `${key} reset`)
      await loadData()
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to reset')
    }
  }

  if (loading) {
    return <section className="page-section"><div className="surface-panel"><div className="surface-panel__content">{isZh ? '加载中...' : 'Loading...'}</div></div></section>
  }

  const categories = Object.keys(settings)

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header" style={{ alignItems: 'center' }}>
            <div>
              <p className="eyebrow">{isZh ? '管理' : 'ADMIN'}</p>
              <h2 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--color-text-bright)' }}>{isZh ? '统一配置' : 'Unified Settings'}</h2>
              <p className="panel-subtitle">{isZh ? '管理所有系统配置，优先级高于 .env 文件' : 'Manage all system settings. Overrides .env file.'}</p>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn--sm" onClick={() => { if (confirm(isZh ? '重置所有配置？' : 'Reset all settings?')) { resetSettings().then(() => loadData()) } }}>
                {isZh ? '全部重置' : 'Reset All'}
              </button>
              <button className="btn btn--sm btn--accent" onClick={handleSave} disabled={saving || Object.keys(edits).length === 0}>
                {saving ? (isZh ? '保存中...' : 'Saving...') : (isZh ? '保存更改' : 'Save Changes')}
              </button>
            </div>
          </div>
          <AdminTabs />
        </div>
      </section>

      {errorMessage && (
        <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(242,92,92,0.2)', background: 'rgba(242,92,92,0.05)', color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
          {errorMessage}
        </div>
      )}
      {noticeMessage && (
        <div style={{ padding: '8px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid rgba(61,214,140,0.2)', background: 'rgba(61,214,140,0.05)', color: 'var(--color-positive)', fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
          {noticeMessage}
        </div>
      )}

      {categories.map((cat) => {
        const items = settings[cat] || []
        const label = CATEGORY_LABELS[cat]
        const catLabel = label ? (isZh ? label.zh : label.en) : cat.toUpperCase()
        const isExpanded = expandedCat === cat

        return (
          <section key={cat} className="surface-panel">
            <div className="surface-panel__content" style={{ padding: '10px 14px' }}>
              <button
                onClick={() => setExpandedCat(isExpanded ? null : cat)}
                style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                  color: 'var(--color-text-bright)', fontFamily: 'var(--font-mono)',
                  fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.06em',
                  textTransform: 'uppercase', padding: '4px 0',
                }}
              >
                <span>{catLabel}</span>
                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.7rem' }}>{isExpanded ? '▲' : '▼'}</span>
              </button>

              {isExpanded && (
                <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
                  {items.map((item: SettingItem) => {
                    const edited = edits[item.key]
                    const displayVal = edited !== undefined ? edited : (item.is_set ? item.value : '')
                    const isEdited = edited !== undefined && edited !== item.value

                    return (
                      <div key={item.key} style={{
                        display: 'grid', gridTemplateColumns: '180px 1fr auto', gap: 8, alignItems: 'center',
                        padding: '6px 8px', borderRadius: 'var(--radius-sm)',
                        background: isEdited ? 'rgba(88,166,255,0.04)' : 'transparent',
                        border: `1px solid ${isEdited ? 'rgba(88,166,255,0.2)' : 'transparent'}`,
                      }}>
                        <div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--color-text-bright)', fontWeight: 500 }}>{item.label}</div>
                          <div style={{ fontSize: '0.6rem', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)' }}>{item.key}</div>
                        </div>
                        <input
                          className="input"
                          type={item.type === 'password' ? 'password' : 'text'}
                          value={displayVal}
                          onChange={(e) => handleEdit(item.key, e.target.value)}
                          placeholder={item.default || ''}
                          style={{ minHeight: 28, fontSize: '0.78rem' }}
                        />
                        <button
                          className="btn btn--ghost btn--sm"
                          onClick={() => handleReset(item.key)}
                          title={isZh ? '重置为默认值' : 'Reset to default'}
                          style={{ minHeight: 26, padding: '0 6px', fontSize: '0.65rem' }}
                        >
                          {isZh ? '重置' : 'Reset'}
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </section>
        )
      })}
    </section>
  )
}
