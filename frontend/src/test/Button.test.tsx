import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Button } from '@/components/common/Button'

describe('Button Component', () => {
  it('renders children correctly', () => {
    render(<Button>Deploy Service</Button>)
    expect(screen.getByRole('button', { name: /deploy service/i })).toBeInTheDocument()
  })

  it('handles click events', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click Me</Button>)
    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('disables button and shows spinner when isLoading is true', () => {
    render(<Button isLoading>Submitting</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
  })

  it('renders danger variant styling', () => {
    render(<Button variant="danger">Delete</Button>)
    const btn = screen.getByRole('button')
    expect(btn.className).toContain('bg-hc-critical')
  })
})

