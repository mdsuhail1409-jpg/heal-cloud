import React, { ButtonHTMLAttributes } from 'react'
import { Loader2 } from 'lucide-react'
import { cn } from '@/utils/cn'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  icon?: React.ReactNode
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  icon,
  className,
  disabled,
  ...props
}) => {
  const baseStyles =
    'inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-hc-bg disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]'

  const variantStyles = {
    primary:
      'bg-hc-accent hover:bg-hc-accentHover text-white shadow-sm focus:ring-hc-accent',
    secondary:
      'bg-hc-card hover:bg-hc-cardHover text-hc-text border border-hc-border focus:ring-hc-border',
    danger:
      'bg-hc-critical hover:bg-red-600 text-white shadow-sm focus:ring-hc-critical',
    ghost:
      'bg-transparent hover:bg-hc-card text-hc-muted hover:text-hc-text focus:ring-hc-border',
    outline:
      'bg-transparent hover:bg-hc-card text-hc-text border border-hc-border hover:border-hc-borderHover focus:ring-hc-accent',
  }

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5',
    md: 'text-sm px-3.5 py-2 gap-2',
    lg: 'text-base px-5 py-2.5 gap-2.5',
  }

  return (
    <button
      className={cn(baseStyles, variantStyles[variant], sizeStyles[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? (
        <Loader2 className="w-4 h-4 animate-spin text-current" />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      {children}
    </button>
  )
}

