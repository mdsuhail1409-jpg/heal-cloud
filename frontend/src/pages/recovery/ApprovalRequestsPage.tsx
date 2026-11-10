import React, { useState, useEffect } from 'react'
import { CheckSquare, Check, X, ShieldAlert, AlertTriangle } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { ApprovalRequest } from '@/types'
import { Table, Column } from '@/components/common/Table'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { Textarea } from '@/components/common/Input'
import { LoadingState, EmptyState } from '@/components/common/Feedback'
import { formatDateTime } from '@/utils/formatters'

export const ApprovalRequestsPage: React.FC = () => {
  const { currentOrg, currentWorkspace } = useAuth()

  const [requests, setRequests] = useState<ApprovalRequest[]>([])
  const [isLoading, setIsLoading] = useState(true)

  // Decision Modal
  const [activeRequest, setActiveRequest] = useState<ApprovalRequest | null>(null)
  const [decisionType, setDecisionType] = useState<'APPROVED' | 'REJECTED'>('APPROVED')
  const [reason, setReason] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const loadRequests = async () => {
    if (!currentOrg || !currentWorkspace) return
    setIsLoading(true)
    try {
      const data = await api.listApprovalRequests(currentOrg.id, currentWorkspace.id)
      setRequests(data)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadRequests()
  }, [currentOrg, currentWorkspace])

  const handleOpenDecision = (req: ApprovalRequest, type: 'APPROVED' | 'REJECTED') => {
    setActiveRequest(req)
    setDecisionType(type)
    setReason('')
  }

  const handleConfirmDecision = async () => {
    if (!currentOrg || !currentWorkspace || !activeRequest) return
    setIsSubmitting(true)
    try {
      await api.decideApproval(
        currentOrg.id,
        currentWorkspace.id,
        activeRequest.id,
        decisionType,
        reason
      )
      await loadRequests()
      setActiveRequest(null)
    } finally {
      setIsSubmitting(false)
    }
  }

  const columns: Column<ApprovalRequest>[] = [
    {
      header: 'Incident / Service',
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
      header: 'Proposed Remediation Action',
      accessor: (r) => (
        <div>
          <span className="font-semibold text-xs text-emerald-400 font-mono">
            {r.proposed_action}
          </span>
          <span className="text-[11px] text-hc-dim block">Blast: {r.blast_radius}</span>
        </div>
      ),
    },
    {
      header: 'Risk Tier',
      accessor: (r) => (
        <Badge
          variant={
            r.risk_tier === 'TIER_3_HIGH'
              ? 'critical'
              : r.risk_tier === 'TIER_2_MEDIUM'
              ? 'warning'
              : 'info'
          }
          size="sm"
        >
          {r.risk_tier}
        </Badge>
      ),
      align: 'center',
    },
    {
      header: 'Status',
      accessor: (r) => (
        <Badge
          variant={
            r.status === 'APPROVED' ? 'healthy' : r.status === 'REJECTED' ? 'critical' : 'warning'
          }
          size="sm"
        >
          {r.status}
        </Badge>
      ),
      align: 'center',
    },
    {
      header: 'Requested At',
      accessor: (r) => (
        <span className="font-mono text-[11px] text-hc-dim">{formatDateTime(r.requested_at)}</span>
      ),
    },
    {
      header: 'Actions',
      accessor: (r) =>
        r.status === 'PENDING' ? (
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="primary"
              onClick={() => handleOpenDecision(r, 'APPROVED')}
              className="bg-emerald-600 hover:bg-emerald-500 text-xs px-2.5 py-1"
              icon={<Check className="w-3 h-3" />}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => handleOpenDecision(r, 'REJECTED')}
              className="text-hc-critical hover:bg-red-950/30 text-xs px-2.5 py-1"
              icon={<X className="w-3 h-3" />}
            >
              Reject
            </Button>
          </div>
        ) : (
          <span className="text-[11px] font-mono text-hc-dim">
            {r.decided_by ? `By: ${r.decided_by}` : 'Decided'}
          </span>
        ),
      align: 'right',
    },
  ]

  const pendingCount = requests.filter((r) => r.status === 'PENDING').length

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-hc-text">
            Human-in-the-Loop (HITL) Approvals
          </h1>
          <p className="text-xs text-hc-muted mt-1">
            Dual-custody safety authorization gate for destructive or high-risk remediation actions
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-hc-dim">
          <span>Pending queue:</span>
          <span className="font-bold text-amber-400">{pendingCount} requests</span>
        </div>
      </div>

      {isLoading ? (
        <LoadingState message="Loading approval requests..." />
      ) : requests.length === 0 ? (
        <EmptyState
          title="Approval Queue Clear"
          description="No autonomous playbooks currently awaiting human authorization."
          icon={<CheckSquare className="w-6 h-6 text-emerald-400" />}
        />
      ) : (
        <Table columns={columns} data={requests} keyExtractor={(r) => r.id} />
      )}

      {/* Decision Modal */}
      <Modal
        isOpen={Boolean(activeRequest)}
        onClose={() => setActiveRequest(null)}
        title={
          decisionType === 'APPROVED'
            ? '⚠️ Authorize Remediation Execution'
            : 'Reject Remediation Action'
        }
        subtitle={`Incident: ${activeRequest?.incident_number} (${activeRequest?.service_name})`}
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-hc-bg border border-hc-border text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-hc-dim">Action:</span>
              <span className="font-semibold text-emerald-400 font-mono">
                {activeRequest?.proposed_action}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-hc-dim">Risk Tier:</span>
              <span className="font-mono text-amber-400">{activeRequest?.risk_tier}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-hc-dim">Blast Radius:</span>
              <span className="text-hc-text">{activeRequest?.blast_radius}</span>
            </div>
          </div>

          <Textarea
            label="Operator Justification / Note"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={
              decisionType === 'APPROVED'
                ? 'Verified system state. Authorizing rollback.'
                : 'Insufficient evidence to warrant service restart.'
            }
            required
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-hc-border">
            <Button type="button" variant="ghost" onClick={() => setActiveRequest(null)}>
              Cancel
            </Button>
            <Button
              variant={decisionType === 'APPROVED' ? 'primary' : 'danger'}
              onClick={handleConfirmDecision}
              isLoading={isSubmitting}
            >
              {decisionType === 'APPROVED' ? '🚀 Authorize Action' : 'Confirm Rejection'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

