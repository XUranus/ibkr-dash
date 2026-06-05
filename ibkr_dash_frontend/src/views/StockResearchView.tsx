import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import SymbolInput from '@/components/SymbolInput'

export default function StockResearchView() {
  const { t } = useTranslation()
  const [symbol, setSymbol] = useState('')

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <p className="eyebrow">{t('stockResearch.research')}</p>
              <h2 style={{ margin: 0, fontSize: '1.55rem' }}>{t('stockResearch.title')}</h2>
              <p className="panel-subtitle">{t('stockResearch.subtitle')}</p>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 0.4fr) minmax(240px, 1fr) auto', gap: 'var(--space-3)', alignItems: 'end' }}>
            <label className="field-stack">
              <span className="field-stack__label">{t('stockResearch.symbol')}</span>
              <SymbolInput value={symbol} onChange={setSymbol} placeholder="AAPL / MSFT / NVDA" />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">{t('stockResearch.query')}</span>
              <input className="input" type="text" placeholder="What analysis do you need?" />
            </label>
            <button className="btn btn--accent">{t('stockResearch.search')}</button>
          </div>
        </div>
      </section>

      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="empty-state" style={{ minHeight: 320 }}>
            {symbol ? t('stockResearch.enterQueryAndSearch', { symbol: symbol.toUpperCase() }) : t('stockResearch.enterSymbolToBegin')}
          </div>
        </div>
      </section>
    </section>
  )
}
