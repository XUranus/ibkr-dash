/** Investment policy page -- view and edit global and per-symbol policies. */

import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { request } from '@/api/http'
import type { GlobalInvestmentPolicy, SymbolInvestmentPolicy } from '@/types/investmentPolicy'

export default function InvestmentPolicyView() {
  const { t } = useTranslation()
  const [globalPolicy, setGlobalPolicy] = useState<GlobalInvestmentPolicy | null>(null)
  const [symbolPolicies, setSymbolPolicies] = useState<SymbolInvestmentPolicy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [gp, sp] = await Promise.all([
        request<GlobalInvestmentPolicy>('/api/investment-policy/global'),
        request<{ items: SymbolInvestmentPolicy[] }>('/api/investment-policy/symbols'),
      ])
      setGlobalPolicy(gp)
      setSymbolPolicies(sp.items || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : t('investmentPolicy.failedToLoad'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => { void loadData() }, [loadData])

  async function handleSeedDefaults() {
    try {
      await request('/api/bootstrap', { method: 'POST' })
      await loadData()
    } catch (err) {
      setError(err instanceof Error ? err.message : t('investmentPolicy.failedToSeed'))
    }
  }

  const selectedPolicy = selectedSymbol
    ? symbolPolicies.find((p) => p.symbol === selectedSymbol)
    : null

  return (
    <section className="page-section">
      <section className="surface-panel" style={{ animation: 'slideUp 0.4s ease' }}>
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <p className="eyebrow">{t('investmentPolicy.eyebrow')}</p>
              <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--color-text-bright)' }}>{t('investmentPolicy.title')}</h2>
              <p className="panel-subtitle">{t('investmentPolicy.subtitle')}</p>
            </div>
          </div>
        </div>
      </section>

      {error && (
        <div className="surface-panel" style={{ marginBottom: 'var(--space-4)', padding: '12px 16px', borderLeft: '3px solid var(--color-negative)' }}>
          <p style={{ color: 'var(--color-negative)', fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{error}</p>
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, marginBottom: 'var(--space-4)' }}>
        <button className="btn btn--accent btn--sm" onClick={handleSeedDefaults}>
          {t('investmentPolicy.seedDefaults')}
        </button>
      </div>

      {loading ? (
        <p style={{ color: 'var(--color-text-muted)' }}>{t('investmentPolicy.loading')}</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: 'var(--space-4)' }}>
          {/* Symbol list */}
          <div className="surface-panel">
            <div className="surface-panel__content" style={{ padding: 12 }}>
              <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: 8 }}>
                {t('investmentPolicy.globalPolicy')}
              </p>
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => setSelectedSymbol(null)}
                style={{
                  width: '100%',
                  justifyContent: 'flex-start',
                  textAlign: 'left',
                  marginBottom: 8,
                  background: !selectedSymbol ? 'rgba(212,168,67,0.08)' : 'transparent',
                  borderColor: !selectedSymbol ? 'rgba(212,168,67,0.2)' : 'transparent',
                  fontSize: '0.82rem',
                }}
              >
                {t('investmentPolicy.globalPolicyTitle')}
              </button>
              <p style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: 8, marginTop: 12 }}>
                {t('investmentPolicy.symbolPolicies', { count: symbolPolicies.length })}
              </p>
              {symbolPolicies.map((p) => (
                <button
                  key={p.symbol}
                  className="btn btn--ghost btn--sm"
                  onClick={() => setSelectedSymbol(p.symbol)}
                  style={{
                    width: '100%',
                    justifyContent: 'flex-start',
                    textAlign: 'left',
                    marginBottom: 4,
                    background: selectedSymbol === p.symbol ? 'rgba(212,168,67,0.08)' : 'transparent',
                    borderColor: selectedSymbol === p.symbol ? 'rgba(212,168,67,0.2)' : 'transparent',
                    fontSize: '0.82rem',
                    opacity: p.enabled ? 1 : 0.5,
                  }}
                >
                  <span style={{ color: 'var(--color-accent-strong)' }}>{p.symbol}</span>
                  <span style={{ marginLeft: 8, color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>
                    {p.asset_role}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Policy detail */}
          <div className="surface-panel">
            <div className="surface-panel__content" style={{ padding: 16 }}>
              {!selectedSymbol && globalPolicy ? (
                <div>
                  <h3 style={{ marginBottom: 16 }}>{t('investmentPolicy.globalPolicyTitle')}</h3>
                  <div style={{ display: 'grid', gap: 12 }}>
                    <PolicyField label={t('investmentPolicy.riskProfile')} value={globalPolicy.risk_profile} />
                    <PolicyField label={t('investmentPolicy.targetAnnualReturn')} value={globalPolicy.target_annual_return_pct ? `${(globalPolicy.target_annual_return_pct * 100).toFixed(1)}%` : '--'} />
                    <PolicyField label={t('investmentPolicy.maxDrawdownTolerance')} value={globalPolicy.max_drawdown_tolerance_pct ? `${(globalPolicy.max_drawdown_tolerance_pct * 100).toFixed(1)}%` : '--'} />
                    <PolicyField label={t('investmentPolicy.allowConcentrated')} value={globalPolicy.allow_concentrated_position ? t('investmentPolicy.yes') : t('investmentPolicy.no')} />
                    <PolicyField label={t('investmentPolicy.allowLeverage')} value={globalPolicy.allow_leverage ? t('investmentPolicy.yes') : t('investmentPolicy.no')} />
                    <PolicyField label={t('investmentPolicy.cashReserve')} value={globalPolicy.cash_reserve_pct ? `${(globalPolicy.cash_reserve_pct * 100).toFixed(1)}%` : '--'} />
                    <PolicyField label={t('investmentPolicy.holdingPeriod')} value={globalPolicy.holding_period || '--'} />
                    <PolicyField label={t('investmentPolicy.notes')} value={globalPolicy.notes || '--'} />
                  </div>
                </div>
              ) : selectedPolicy ? (
                <div>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
                    <h3 style={{ margin: 0 }}>{selectedPolicy.symbol}</h3>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
                      {selectedPolicy.asset_role} / {selectedPolicy.conviction}
                    </span>
                    {!selectedPolicy.enabled && (
                      <span style={{ color: 'var(--color-text-muted)', fontSize: '0.72rem' }}>{t('investmentPolicy.disabled')}</span>
                    )}
                  </div>
                  <div style={{ display: 'grid', gap: 12 }}>
                    <PolicyField label={t('investmentPolicy.assetRole')} value={selectedPolicy.asset_role} />
                    <PolicyField label={t('investmentPolicy.conviction')} value={selectedPolicy.conviction} />
                    <PolicyField label={t('investmentPolicy.targetPosition')} value={selectedPolicy.user_preferred_target_position_pct ? `${(selectedPolicy.user_preferred_target_position_pct * 100).toFixed(1)}%` : '--'} />
                    <PolicyField label={t('investmentPolicy.maxPosition')} value={`${(selectedPolicy.user_preferred_max_position_pct * 100).toFixed(1)}%`} />
                    <PolicyField label={t('investmentPolicy.minPosition')} value={`${(selectedPolicy.user_preferred_min_position_pct * 100).toFixed(1)}%`} />
                    {selectedPolicy.add_rules.length > 0 && (
                      <PolicyListField label={t('investmentPolicy.addRules')} items={selectedPolicy.add_rules} />
                    )}
                    {selectedPolicy.sell_triggers.length > 0 && (
                      <PolicyListField label={t('investmentPolicy.sellTriggers')} items={selectedPolicy.sell_triggers} />
                    )}
                    {selectedPolicy.no_add_triggers.length > 0 && (
                      <PolicyListField label={t('investmentPolicy.noAddTriggers')} items={selectedPolicy.no_add_triggers} />
                    )}
                    <PolicyField label={t('investmentPolicy.notes')} value={selectedPolicy.notes || '--'} />
                  </div>
                </div>
              ) : (
                <p style={{ color: 'var(--color-text-muted)' }}>{t('investmentPolicy.selectPolicy')}</p>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

function PolicyField({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'baseline' }}>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)', minWidth: 140 }}>
        {label}
      </span>
      <span style={{ fontSize: '0.85rem', color: 'var(--color-text-primary)' }}>{value}</span>
    </div>
  )
}

function PolicyListField({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--color-text-muted)' }}>
        {label}
      </span>
      <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
        {items.map((item, i) => (
          <li key={i} style={{ fontSize: '0.82rem', color: 'var(--color-text-primary)', marginBottom: 2 }}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}
