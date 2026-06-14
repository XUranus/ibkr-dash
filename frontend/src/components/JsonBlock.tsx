import { useState, useCallback, useMemo } from 'react'

interface JsonBlockProps {
  value: unknown
  collapsed?: boolean
  title?: string
}

export default function JsonBlock({ value, collapsed = false, title }: JsonBlockProps) {
  const [collapsedState, setCollapsedState] = useState(collapsed)

  const jsonText = useMemo(() => {
    try {
      return JSON.stringify(value ?? null, null, 2)
    } catch {
      return String(value)
    }
  }, [value])

  const handleToggle = useCallback(() => {
    setCollapsedState((prev) => !prev)
  }, [])

  return (
    <div className="json-block">
      {(title || collapsedState) && (
        <button type="button" className="json-block__toggle" onClick={handleToggle}>
          <span>{title || 'JSON'}</span>
          <span>{collapsedState ? '▼' : '▲'}</span>
        </button>
      )}
      {!collapsedState && (
        <pre style={{
          maxHeight: 420,
          margin: 0,
          padding: 12,
          overflow: 'auto',
          border: '1px solid rgba(129, 160, 207, 0.14)',
          borderRadius: 'var(--radius-sm)',
          background: 'rgba(4, 10, 20, 0.72)',
          color: 'var(--color-text-secondary)',
          fontSize: '0.8rem',
          lineHeight: 1.55,
          whiteSpace: 'pre-wrap',
          overflowWrap: 'anywhere',
        }}>
          {jsonText}
        </pre>
      )}
    </div>
  )
}
