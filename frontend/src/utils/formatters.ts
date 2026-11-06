export function formatRelativeTime(dateString?: string | null): string {
  if (!dateString) return 'Never'
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHour = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHour / 24)

  if (diffSec < 5) return 'just now'
  if (diffSec < 60) return `${diffSec}s ago`
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHour < 24) return `${diffHour}h ago`
  return `${diffDay}d ago`
}

export function formatDateTime(dateString?: string | null): string {
  if (!dateString) return '—'
  const date = new Date(dateString)
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

export function formatLatency(latencyMs?: number | null): string {
  if (latencyMs === null || latencyMs === undefined) return '—'
  if (latencyMs < 1000) return `${latencyMs.toFixed(1)}ms`
  return `${(latencyMs / 1000).toFixed(2)}s`
}

export function formatDuration(durationSec?: number | null): string {
  if (!durationSec) return '—'
  if (durationSec < 60) return `${durationSec}s`
  const minutes = Math.floor(durationSec / 60)
  const seconds = durationSec % 60
  return `${minutes}m ${seconds}s`
}
