import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ErrorBlock from '../ErrorBlock'

describe('ErrorBlock', () => {
  it('renders the error message', () => {
    render(<ErrorBlock message="Something went wrong" />)
    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
  })

  it('renders a warning icon', () => {
    const { container } = render(<ErrorBlock message="Error occurred" />)
    expect(container.textContent).toContain('⚠')
  })

  it('renders different messages', () => {
    const { rerender } = render(<ErrorBlock message="First error" />)
    expect(screen.getByText('First error')).toBeInTheDocument()

    rerender(<ErrorBlock message="Second error" />)
    expect(screen.getByText('Second error')).toBeInTheDocument()
  })
})
