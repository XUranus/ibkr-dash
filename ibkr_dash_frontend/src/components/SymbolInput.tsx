import { useState, useCallback, useRef, useEffect } from 'react'

interface Props {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  required?: boolean
}

export default function SymbolInput({ value, onChange, placeholder, required }: Props) {
  return (
    <input
      className="input"
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder || 'AAPL / MSFT / NVDA'}
      required={required}
      autoComplete="off"
      style={{ textTransform: 'uppercase' }}
    />
  )
}
