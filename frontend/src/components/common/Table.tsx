import React from 'react'
import { cn } from '@/utils/cn'

export interface Column<T> {
  header: string
  accessor?: keyof T | ((row: T) => React.ReactNode)
  className?: string
  align?: 'left' | 'center' | 'right'
}

export interface TableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyExtractor: (row: T) => string
  onRowClick?: (row: T) => void
  emptyMessage?: string
  className?: string
}

export function Table<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  emptyMessage = 'No records found.',
  className,
}: TableProps<T>) {
  return (
    <div className={cn('w-full overflow-x-auto rounded-xl border border-hc-border bg-hc-card', className)}>
      <table className="w-full text-left text-sm text-hc-text border-collapse">
        <thead>
          <tr className="border-b border-hc-border bg-hc-bg/40 text-xs font-semibold text-hc-muted tracking-wide uppercase">
            {columns.map((col, idx) => (
              <th
                key={idx}
                className={cn(
                  'px-4 py-3 select-none',
                  col.align === 'center' && 'text-center',
                  col.align === 'right' && 'text-right',
                  col.className
                )}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-hc-border/60">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center text-sm text-hc-dim">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={keyExtractor(row)}
                onClick={() => onRowClick?.(row)}
                className={cn(
                  'transition-colors hover:bg-hc-cardHover/60',
                  onRowClick && 'cursor-pointer'
                )}
              >
                {columns.map((col, colIdx) => {
                  let content: React.ReactNode
                  if (typeof col.accessor === 'function') {
                    content = col.accessor(row)
                  } else if (col.accessor) {
                    content = String(row[col.accessor] ?? '—')
                  } else {
                    content = null
                  }

                  return (
                    <td
                      key={colIdx}
                      className={cn(
                        'px-4 py-3.5 text-xs text-hc-text whitespace-nowrap',
                        col.align === 'center' && 'text-center',
                        col.align === 'right' && 'text-right',
                        col.className
                      )}
                    >
                      {content}
                    </td>
                  )
                })}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
