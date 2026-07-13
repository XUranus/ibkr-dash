import { useState, useMemo, useEffect } from 'react'

interface JsonBlockProps {
  value: unknown
  collapsed?: boolean
  title?: string
  onCollapsedChange?: (collapsed: boolean) => void
}

export default function JsonBlock({ value, collapsed = false, title, onCollapsedChange }: JsonBlockProps) {
  const [collapsedState, setCollapsedState] = useState(collapsed)

  useEffect(() => { setCollapsedState(collapsed) }, [collapsed])

  function toggle() {
    const next = !collapsedState
    setCollapsedState(next)
    onCollapsedChange?.(next)
  }

  const jsonText = useMemo(() => JSON.stringify(value ?? null, null, 2), [value])

  return (
    <div className="json-block">
      {(title || collapsedState) && (
        <button type="button" className="json-block__toggle" onClick={toggle}>
          <span>{title || 'JSON'}</span>
          <span>{collapsedState ? '▼' : '▲'}</span>
        </button>
      )}
      {!collapsedState && <pre>{jsonText}</pre>}
    </div>
  )
}
