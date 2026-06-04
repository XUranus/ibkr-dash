import { useState } from 'react'
import SymbolInput from '@/components/SymbolInput'

export default function StockResearchView() {
  const [symbol, setSymbol] = useState('')

  return (
    <section className="page-section">
      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="section-header">
            <div>
              <p className="eyebrow">RESEARCH</p>
              <h2 style={{ margin: 0, fontSize: '1.55rem' }}>Stock Research</h2>
              <p className="panel-subtitle">View financials, valuation, quotes, and peer analysis for any symbol.</p>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 0.4fr) minmax(240px, 1fr) auto', gap: 'var(--space-3)', alignItems: 'end' }}>
            <label className="field-stack">
              <span className="field-stack__label">Symbol</span>
              <SymbolInput value={symbol} onChange={setSymbol} placeholder="AAPL / MSFT / NVDA" />
            </label>
            <label className="field-stack">
              <span className="field-stack__label">Query</span>
              <input className="input" type="text" placeholder="What analysis do you need?" />
            </label>
            <button className="btn btn--accent">Search</button>
          </div>
        </div>
      </section>

      <section className="surface-panel">
        <div className="surface-panel__content">
          <div className="empty-state" style={{ minHeight: 320 }}>
            {symbol ? `Enter a query and click Search to analyze ${symbol.toUpperCase()}` : 'Enter a stock symbol to begin research'}
          </div>
        </div>
      </section>
    </section>
  )
}
