import React, { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes, forwardRef, useEffect, useRef } from 'react'
import { Search } from 'lucide-react'
import { cn } from '@/utils/cn'

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  helperText?: string
}

export const TextInput = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className, id, ...props }, ref) => {
    const inputId = id || props.name || Math.random().toString(36).substring(2, 9)

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={inputId} className="block text-xs font-medium text-hc-muted">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            'w-full bg-hc-card border border-hc-border rounded-lg px-3 py-2 text-sm text-hc-text placeholder-hc-dim focus:outline-none focus:border-hc-accent focus:ring-1 focus:ring-hc-accent transition-colors disabled:opacity-50 disabled:bg-hc-bg',
            error && 'border-hc-critical focus:border-hc-critical focus:ring-hc-critical',
            className
          )}
          {...props}
        />
        {error ? (
          <p className="text-xs text-hc-critical">{error}</p>
        ) : helperText ? (
          <p className="text-xs text-hc-dim">{helperText}</p>
        ) : null}
      </div>
    )
  }
)
TextInput.displayName = 'TextInput'

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options?: { value: string | number; label: string }[]
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, children, className, id, ...props }, ref) => {
    const selectId = id || props.name || Math.random().toString(36).substring(2, 9)

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={selectId} className="block text-xs font-medium text-hc-muted">
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={cn(
            'w-full bg-hc-card border border-hc-border rounded-lg px-3 py-2 text-sm text-hc-text focus:outline-none focus:border-hc-accent focus:ring-1 focus:ring-hc-accent transition-colors disabled:opacity-50',
            error && 'border-hc-critical',
            className
          )}
          {...props}
        >
          {options
            ? options.map((opt) => (
                <option key={opt.value} value={opt.value} className="bg-hc-card text-hc-text">
                  {opt.label}
                </option>
              ))
            : children}
        </select>
        {error && <p className="text-xs text-hc-critical">{error}</p>}
      </div>
    )
  }
)
Select.displayName = 'Select'

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ label, error, className, id, ...props }, ref) => {
    const areaId = id || props.name || Math.random().toString(36).substring(2, 9)

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label htmlFor={areaId} className="block text-xs font-medium text-hc-muted">
            {label}
          </label>
        )}
        <textarea
          ref={ref}
          id={areaId}
          className={cn(
            'w-full bg-hc-card border border-hc-border rounded-lg px-3 py-2 text-sm text-hc-text placeholder-hc-dim focus:outline-none focus:border-hc-accent focus:ring-1 focus:ring-hc-accent transition-colors disabled:opacity-50 min-h-[80px]',
            error && 'border-hc-critical',
            className
          )}
          {...props}
        />
        {error && <p className="text-xs text-hc-critical">{error}</p>}
      </div>
    )
  }
)
Textarea.displayName = 'Textarea'

export interface SearchInputProps extends InputHTMLAttributes<HTMLInputElement> {
  onSearchChange?: (query: string) => void
}

export const SearchInput: React.FC<SearchInputProps> = ({
  placeholder = 'Search services, incidents, logs...',
  onSearchChange,
  className,
  ...props
}) => {
  const inputRef = useRef<HTMLInputElement>(null)

  // Global '/' keyboard shortcut focus
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className={cn('relative flex items-center w-full max-w-md', className)}>
      <Search className="absolute left-3 w-4 h-4 text-hc-dim pointer-events-none" />
      <input
        ref={inputRef}
        type="text"
        placeholder={placeholder}
        onChange={(e) => onSearchChange?.(e.target.value)}
        className="w-full bg-hc-card/80 border border-hc-border rounded-lg pl-9 pr-8 py-1.5 text-xs text-hc-text placeholder-hc-dim focus:outline-none focus:border-hc-accent focus:ring-1 focus:ring-hc-accent transition-colors"
        {...props}
      />
      <kbd className="absolute right-2.5 px-1.5 py-0.5 text-[10px] font-mono text-hc-dim bg-hc-border/50 border border-hc-border rounded pointer-events-none">
        /
      </kbd>
    </div>
  )
}
