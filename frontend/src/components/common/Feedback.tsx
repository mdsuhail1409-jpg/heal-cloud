import React from 'react'
import { AlertTriangle, AlertCircle, RefreshCw, FolderSearch } from 'lucide-react'
import { Button } from './Button'
import { cn } from '@/utils/cn'

export interface EmptyStateProps {
  title: string
  description?: string
  actionLabel?: string
  onAction?: () => void
  icon?: React.ReactNode
  className?: string
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionLabel,
  onAction,
  icon,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-8 text-center rounded-xl border border-dashed border-hc-border/80 bg-hc-card/30',
        className
      )}
    >
      <div className="w-12 h-12 flex items-center justify-center rounded-xl bg-hc-border/30 text-hc-dim mb-3">
        {icon || <FolderSearch className="w-6 h-6" />}
      </div>
      <h3 className="text-sm font-semibold text-hc-text">{title}</h3>
      {description && <p className="text-xs text-hc-muted max-w-sm mt-1">{description}</p>}
      {actionLabel && onAction && (
        <Button size="sm" onClick={onAction} className="mt-4">
          {actionLabel}
        </Button>
      )}
    </div>
  )
}

export const LoadingState: React.FC<{ message?: string; className?: string }> = ({
  message = 'Loading platform telemetry...',
  className,
}) => {
  return (
    <div className={cn('flex flex-col items-center justify-center p-12 space-y-3', className)}>
      <RefreshCw className="w-6 h-6 text-hc-accent animate-spin" />
      <span className="text-xs text-hc-muted font-mono">{message}</span>
    </div>
  )
}

export interface ErrorBannerProps {
  title?: string
  message: string
  onRetry?: () => void
  className?: string
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({
  title = 'An error occurred',
  message,
  onRetry,
  className,
}) => {
  return (
    <div
      className={cn(
        'flex items-start justify-between gap-3 p-4 rounded-xl border border-hc-critical/40 bg-red-950/20 text-red-300',
        className
      )}
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-hc-critical shrink-0 mt-0.5" />
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-red-200">{title}</h4>
          <p className="text-xs text-red-300/90 mt-0.5">{message}</p>
        </div>
      </div>
      {onRetry && (
        <Button variant="danger" size="sm" onClick={onRetry} className="shrink-0 text-xs">
          Retry
        </Button>
      )}
    </div>
  )
}

export const DemoBanner: React.FC<{ featureName: string }> = ({ featureName }) => {
  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-blue-950/40 border border-blue-800/40 text-blue-300 text-xs mb-4">
      <AlertTriangle className="w-4 h-4 text-blue-400 shrink-0" />
      <span>
        <strong>Preview & Demonstration Mode:</strong> Displaying high-fidelity preview records for{' '}
        <span className="font-mono text-white">{featureName}</span>. Connects to backend self-healing worker in Phase 8.
      </span>
    </div>
  )
}
