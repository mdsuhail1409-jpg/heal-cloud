import React from 'react'
import {
  HealthStatusEnum,
  IncidentSeverityEnum,
  IncidentStatusEnum,
} from '@/types'
import { cn } from '@/utils/cn'

export interface BadgeProps {
  children?: React.ReactNode
  variant?: 'healthy' | 'warning' | 'critical' | 'info' | 'neutral'
  size?: 'sm' | 'md'
  dot?: boolean
  className?: string
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  dot = false,
  className,
}) => {
  const styles = {
    healthy: 'bg-emerald-950/60 text-emerald-400 border-emerald-800/60',
    warning: 'bg-amber-950/60 text-amber-400 border-amber-800/60',
    critical: 'bg-red-950/60 text-red-400 border-red-800/60',
    info: 'bg-blue-950/60 text-blue-400 border-blue-800/60',
    neutral: 'bg-gray-800/60 text-gray-400 border-gray-700/60',
  }

  const dotColors = {
    healthy: 'bg-emerald-400',
    warning: 'bg-amber-400',
    critical: 'bg-red-400 animate-pulse',
    info: 'bg-blue-400',
    neutral: 'bg-gray-400',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center font-mono font-medium border rounded-md uppercase tracking-wider',
        size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-0.5 text-xs',
        styles[variant],
        className
      )}
    >
      {dot && <span className={cn('w-1.5 h-1.5 rounded-full mr-1.5 shrink-0', dotColors[variant])} />}
      {children}
    </span>
  )
}

export const HealthBadge: React.FC<{ status?: HealthStatusEnum | string; size?: 'sm' | 'md' }> = ({
  status = 'UNKNOWN',
  size = 'md',
}) => {
  switch (status) {
    case 'HEALTHY':
      return <Badge variant="healthy" size={size} dot>Healthy</Badge>
    case 'DEGRADED':
      return <Badge variant="warning" size={size} dot>Degraded</Badge>
    case 'UNHEALTHY':
      return <Badge variant="critical" size={size} dot>Unhealthy</Badge>
    default:
      return <Badge variant="neutral" size={size} dot>Unknown</Badge>
  }
}

export const SeverityBadge: React.FC<{ severity: IncidentSeverityEnum | string; size?: 'sm' | 'md' }> = ({
  severity,
  size = 'md',
}) => {
  switch (severity) {
    case 'P1_CRITICAL':
      return <Badge variant="critical" size={size} dot>P1 Critical</Badge>
    case 'P2_HIGH':
      return <Badge variant="warning" size={size} dot>P2 High</Badge>
    case 'P3_MEDIUM':
      return <Badge variant="info" size={size}>P3 Medium</Badge>
    case 'P4_LOW':
      return <Badge variant="neutral" size={size}>P4 Low</Badge>
    default:
      return <Badge variant="neutral" size={size}>{severity}</Badge>
  }
}

export const IncidentStatusBadge: React.FC<{ status: IncidentStatusEnum | string; size?: 'sm' | 'md' }> = ({
  status,
  size = 'md',
}) => {
  switch (status) {
    case 'OPEN':
      return <Badge variant="critical" size={size} dot>Open</Badge>
    case 'ACKNOWLEDGED':
      return <Badge variant="warning" size={size}>Acknowledged</Badge>
    case 'INVESTIGATING':
      return <Badge variant="info" size={size} dot>Investigating</Badge>
    case 'RECOVERY_PENDING':
    case 'RECOVERING':
      return <Badge variant="info" size={size} dot>Recovering</Badge>
    case 'RESOLVED':
      return <Badge variant="healthy" size={size}>Resolved</Badge>
    case 'CLOSED':
      return <Badge variant="neutral" size={size}>Closed</Badge>
    case 'FAILED':
      return <Badge variant="critical" size={size}>Failed</Badge>
    default:
      return <Badge variant="neutral" size={size}>{status}</Badge>
  }
}

