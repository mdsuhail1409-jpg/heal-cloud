import React from 'react'
import { cn } from '@/utils/cn'

export interface SparklineProps {
  data: number[]
  width?: number
  height?: number
  color?: string
  className?: string
}

export const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 140,
  height = 36,
  color = '#3B82F6',
  className,
}) => {
  if (!data || data.length < 2) {
    return <span className="text-[10px] text-hc-dim font-mono">No telemetry</span>
  }

  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1

  const points = data
    .map((val, idx) => {
      const x = (idx / (data.length - 1)) * (width - 4) + 2
      const y = height - ((val - min) / range) * (height - 8) - 4
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')

  return (
    <svg width={width} height={height} className={cn('overflow-visible shrink-0', className)}>
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  )
}

export interface LatencyBarChartProps {
  samples: { timestamp: string; response_time_ms: number; is_successful: boolean }[]
  height?: number
  className?: string
}

export const LatencyBarChart: React.FC<LatencyBarChartProps> = ({
  samples,
  height = 120,
  className,
}) => {
  if (!samples || samples.length === 0) {
    return (
      <div className="flex items-center justify-center h-28 text-xs text-hc-dim font-mono">
        No metric samples recorded
      </div>
    )
  }

  const values = samples.map((s) => s.response_time_ms)
  const maxVal = Math.max(...values, 200)

  return (
    <div className={cn('w-full flex flex-col space-y-2', className)}>
      <div className="flex items-end gap-1.5 w-full h-28 pt-4 pb-2 border-b border-hc-border/60">
        {samples.slice(-24).map((sample, idx) => {
          const barHeight = Math.max(Math.round((sample.response_time_ms / maxVal) * 80), 4)
          const barColor = !sample.is_successful
            ? 'bg-hc-critical'
            : sample.response_time_ms > 1000
            ? 'bg-hc-warning'
            : 'bg-hc-accent'

          return (
            <div
              key={idx}
              className="flex-1 flex flex-col items-center justify-end group relative h-full"
            >
              <div
                style={{ height: `${barHeight}%` }}
                className={cn('w-full rounded-t transition-all group-hover:opacity-80', barColor)}
              />
              {/* Tooltip */}
              <div className="absolute bottom-full mb-1 hidden group-hover:flex flex-col items-center z-20 pointer-events-none">
                <div className="bg-hc-card border border-hc-border px-2 py-1 rounded shadow text-[10px] text-hc-text whitespace-nowrap font-mono">
                  {sample.response_time_ms.toFixed(1)}ms {sample.is_successful ? 'OK' : 'FAIL'}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <div className="flex justify-between text-[10px] text-hc-dim font-mono">
        <span>Earliest</span>
        <span>Peak: {maxVal.toFixed(0)}ms</span>
        <span>Latest</span>
      </div>
    </div>
  )
}
