import React from 'react'
import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { HealthBadge, SeverityBadge, IncidentStatusBadge } from '@/components/common/Badge'

describe('Badge Components', () => {
  it('renders healthy badge with dot indicator', () => {
    render(<HealthBadge status="HEALTHY" />)
    expect(screen.getByText('Healthy')).toBeInTheDocument()
  })

  it('renders critical degraded and unhealthy status badges', () => {
    const { rerender } = render(<HealthBadge status="DEGRADED" />)
    expect(screen.getByText('Degraded')).toBeInTheDocument()

    rerender(<HealthBadge status="UNHEALTHY" />)
    expect(screen.getByText('Unhealthy')).toBeInTheDocument()
  })

  it('renders P1 critical severity badge with alert style', () => {
    render(<SeverityBadge severity="P1_CRITICAL" />)
    expect(screen.getByText('P1 Critical')).toBeInTheDocument()
  })

  it('renders incident statuses properly', () => {
    const { rerender } = render(<IncidentStatusBadge status="OPEN" />)
    expect(screen.getByText('Open')).toBeInTheDocument()

    rerender(<IncidentStatusBadge status="RESOLVED" />)
    expect(screen.getByText('Resolved')).toBeInTheDocument()
  })
})
