import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import LoadingBlock from '../LoadingBlock'

describe('LoadingBlock', () => {
  it('renders without crashing', () => {
    const { container } = render(<LoadingBlock />)
    expect(container.firstChild).toBeTruthy()
  })

  it('renders skeleton placeholder elements', () => {
    const { container } = render(<LoadingBlock />)
    // The component renders 4 card placeholders + 1 header + 5 row placeholders
    const surfacePanel = container.querySelector('.surface-panel')
    expect(surfacePanel).toBeInTheDocument()
  })

  it('contains the skeleton-wave animation style', () => {
    const { container } = render(<LoadingBlock />)
    const style = container.querySelector('style')
    expect(style).toBeTruthy()
    expect(style?.textContent).toContain('skeleton-wave')
  })
})
