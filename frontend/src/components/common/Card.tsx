import React, { HTMLAttributes } from 'react'
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react'
import { cn } from '@/utils/cn'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  glow?: boolean
}

export const Card: React.FC<CardProps> = ({ children, glow = false, className, ...props }) => {
  return (
    <div
      className={cn(
        'bg-hc-card border border-hc-border rounded-xl p-5 shadow-card transition-all',
        glow && 'border-hc-accent/40 shadow-[0_0_20px_-5px_rgba(59,130,246,0.2)]',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

export interface MetricKpiCardProps {
  title: string
  value: string | number
  change?: string
  trend?: 'up' | 'down' | 'neutral'
  subtitle?: string
  icon?: React.ReactNode
  variant?: 'default' | 'critical' | 'warning' | 'healthy'
  className?: string
}

export const MetricKpiCard: React.FC<MetricKpiCardProps> = ({
  title,
  value,
  change,
  trend = 'neutral',
  subtitle,
  icon,
  variant = 'default',
  className,
}) => {
  const variantBorder = {
    default: 'border-hc-border hover:border-hc-borderHover',
    critical: 'border-hc-critical/40 hover:border-hc-critical',
    warning: 'border-hc-warning/40 hover:border-hc-warning',
    healthy: 'border-hc-healthy/40 hover:border-hc-healthy',
  }

  return (
    <Card className={cn('flex flex-col justify-between', variantBorder[variant], className)}>
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium text-hc-muted tracking-wide uppercase">{title}</span>
        {icon && <div className="text-hc-dim p-1.5 rounded-lg bg-hc-border/30">{icon}</div>}
      </div>

      <div className="mt-4 flex items-baseline gap-2.5">
        <span className="text-2xl font-bold font-mono tracking-tight text-hc-text">{value}</span>
        {change && (
          <span
            className={cn(
              'inline-flex items-center text-xs font-medium',
              trend === 'up' && 'text-hc-healthy',
              trend === 'down' && 'text-hc-critical',
              trend === 'neutral' && 'text-hc-dim'
            )}
          >
            {trend === 'up' && <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />}
            {trend === 'down' && <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />}
            {trend === 'neutral' && <Minus className="w-3.5 h-3.5 mr-0.5" />}
            {change}
          </span>
        )}
      </div>

      {subtitle && <p className="mt-1.5 text-xs text-hc-dim">{subtitle}</p>}
    </Card>
  )
}

