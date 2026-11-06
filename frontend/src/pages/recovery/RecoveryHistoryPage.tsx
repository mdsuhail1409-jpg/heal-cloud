import React, { useState, useEffect } from 'react'
import { History, CheckCircle, XCircle } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { RecoveryExecution } from '@/types'
import { Table, Column } from '@/components/common/Table'
import { Badge } from '@/components/common/Badge'
import { DemoBanner, LoadingState, EmptyState } from '@/components/common/Feedback'
import { formatDateTime, formatDuration } from '@/utils/formatters'

export const RecoveryHistoryPage: React.FC = () => {
  const { currentOrg, currentWorkspace } = useAuth()

  const [history, setHistory] = useState<RecoveryExecution[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const loadHistory = async () => {
    if (!currentOrg || !currentWorkspace) return
    setIsLoading(true)
    try {
      const data = await api.listRecoveryHistory(currentOrg.id, currentWorkspace.id)
      setHistory(data)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [currentOrg, currentWorkspace])

  const columns: Column<RecoveryExecution>[] = [
    {
      header: 'Incident / Target',
      accessor: (r) => (
        <div>
          <span className="font-mono text-xs font-semibold text-hc-muted">
            {r.incident_number}
          </span>
          <span className="text-xs font-medium text-hc-text block">{r.service_name}</span>
        </div>
      ),
    },
    {
      header: 'Executed Action',
      accessor: (r) => (
        <div>
          <span className="font-mono text-xs font-semibold text-emerald-400">
            {r.action_taken}
          </span>
          <span className="text-[11px] text-hc-dim block">{r.policy_name}</span>
        </div>
      ),
    },
    {
      header: 'Status',
      accessor: (r) => (
        <Badge
          variant={r.status === 'SUCCESS' ? 'healthy' : 'critical'}
          size="sm"
        >
          {r.status}
        </Badge>
      ),
      align: 'center',
    },
    {
      header: 'Verification Result',
      accessor: (r) =>
        r.verification_passed ? (
          <span className="inline-flex items-center text-xs text-emerald-400 font-medium">
            <CheckCircle className="w-3.5 h-3.5 mr-1" /> Verified Healthy
          </span>
        ) : (
          <span className="inline-flex items-center text-xs text-hc-critical font-medium">
            <XCircle className="w-3.5 h-3.5 mr-1" /> Probe Failed
          </span>
        ),
    },
    {
      header: 'Duration',
      accessor: (r) => (
        <span className="font-mono text-xs text-hc-text">
          {r.duration_ms ? `${(r.duration_ms / 1000).toFixed(2)}s` : '—'}
        </span>
      ),
      align: 'right',
    },
    {
      header: 'Started At',
      accessor: (r) => (
        <span className="font-mono text-[11px] text-hc-dim">{formatDateTime(r.started_at)}</span>
      ),
    },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-hc-text">Recovery Execution History</h1>
        <p className="text-xs text-hc-muted mt-1">
          Historical log of automated and human-approved remediations with closed-loop verification proofs
        </p>
      </div>

      <DemoBanner featureName="Recovery History Ledger" />

      {isLoading ? (
        <LoadingState message="Loading recovery history..." />
      ) : history.length === 0 ? (
        <EmptyState
          title="No Executions Recorded"
          description="Autonomous or simulated recovery runs will be permanently recorded here."
          icon={<History className="w-6 h-6" />}
        />
      ) : (
        <Table columns={columns} data={history} keyExtractor={(r) => r.id} />
      )}
    </div>
  )
}
