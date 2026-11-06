import React, { useEffect } from 'react'
import { X } from 'lucide-react'
import { cn } from '@/utils/cn'

export interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  subtitle?: string
  children: React.ReactNode
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = 'md',
  className,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const maxWidthStyles = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Dialog Content */}
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'relative w-full bg-hc-card border border-hc-border rounded-xl shadow-modal overflow-hidden z-10 animate-in fade-in zoom-in-95 duration-150',
          maxWidthStyles[maxWidth],
          className
        )}
      >
        <div className="flex items-start justify-between border-b border-hc-border px-6 py-4">
          <div>
            <h3 className="text-base font-semibold text-hc-text tracking-tight">{title}</h3>
            {subtitle && <p className="text-xs text-hc-muted mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="text-hc-dim hover:text-hc-text p-1 rounded-lg hover:bg-hc-border/40 transition-colors"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="px-6 py-5 max-h-[80vh] overflow-y-auto">{children}</div>
      </div>
    </div>
  )
}
