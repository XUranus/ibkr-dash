import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import StatCard from '../StatCard'

describe('StatCard', () => {
  it('renders the title and value', () => {
    render(<StatCard title="Total Equity" value="$123,456.78" />)
    expect(screen.getByText('Total Equity')).toBeInTheDocument()
    expect(screen.getByText('$123,456.78')).toBeInTheDocument()
  })

  it('renders helper text when provided', () => {
    render(<StatCard title="Cash" value="$10,000" helper="Available balance" />)
    expect(screen.getByText('Available balance')).toBeInTheDocument()
  })

  it('renders delta values when provided', () => {
    render(
      <StatCard
        title="P&L"
        value="+$500"
        deltaAmount="+$50"
        deltaPercent="+2.5%"
        deltaTone="positive"
      />,
    )
    expect(screen.getByText('+$50')).toBeInTheDocument()
    expect(screen.getByText('+2.5%')).toBeInTheDocument()
  })

  it('does not render delta section when no delta props are given', () => {
    const { container } = render(<StatCard title="Simple" value="100" />)
    expect(screen.getByText('Simple')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
    // The delta container should not contain any text
    const deltaElements = container.querySelectorAll('[style*="position: absolute"]')
    expect(deltaElements).toHaveLength(0)
  })
})
