import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MetricKpiCard } from '@/components/common/Card'

describe('MetricKpiCard Component', () => {
  it('renders title and value with monospace formatting', () => {
    render(<MetricKpiCard title="Mean MTTR" value="2m 14s" change="-68%" trend="up" />)
    expect(screen.getByText('Mean MTTR')).toBeInTheDocument()
    expect(screen.getByText('2m 14s')).toBeInTheDocument()
    expect(screen.getByText('-68%')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    render(
      <MetricKpiCard
        title="Auto-Heal Rate"
        value="94.2%"
        subtitle="Verified closed-loop resolution"
      />
    )
    expect(screen.getByText('Verified closed-loop resolution')).toBeInTheDocument()
  })
})

