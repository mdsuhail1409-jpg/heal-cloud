import React, { useState, useEffect } from 'react'
import { FileText, Shield, Search } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { AuditLog } from '@/types'
import { Table, Column } from '@/components/common/Table'
import { Badge } from '@/components/common/Badge'
import { Modal } from '@/components/common/Modal'
import { DemoBanner, LoadingState, EmptyState } from '@/components/common/Feedback'
import { formatDateTime } from '@/utils/formatters'

export const AuditLogsPage: React.FC = () => {
  const { currentOrg } = useAuth()

  const [logs, setLogs] = useState<AuditLog[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null)

  const loadLogs = async () => {
    if (!currentOrg) return
    setIsLoading(true)
    try {
      const data = await api.listAuditLogs(currentOrg.id)
      setLogs(data)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadLogs()
  }, [currentOrg])

  const filteredLogs = logs.filter(
    (l) =>
      l.user_email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      l.resource_type.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const columns: Column<AuditLog>[] = [
    {
      header: 'Timestamp',
      accessor: (l) => (
        <span className="font-mono text-xs text-hc-dim">{formatDateTime(l.created_at)}</span>
      ),
    },
    {
      header: 'Actor',
      accessor: (l) => (
        <span className="font-mono text-xs text-hc-text font-semibold">{l.user_email}</span>
      ),
    },
    {
      header: 'Action',
      accessor: (l) => (
        <Badge variant="info" size="sm">
          {l.action}
        </Badge>
      ),
      align: 'center',
    },
    {
      header: 'Resource',
      accessor: (l) => (
        <div className="font-mono text-xs text-hc-muted truncate max-w-xs">
          <span>{l.resource_type}</span>: <span className="text-hc-dim">{l.resource_id}</span>
        </div>
      ),
    },
    {
      header: 'IP Address',
      accessor: (l) => (
        <span className="font-mono text-xs text-hc-dim">{l.ip_address || '—'}</span>
      ),
    },
    {
      header: 'Details',
      accessor: (l) => (
        <button
          onClick={() => setSelectedLog(l)}
          className="text-xs text-hc-accent hover:underline font-mono"
        >
          View Payload
        </button>
      ),
      align: 'right',
    },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-hc-text">Immutable Audit Ledger</h1>
          <p className="text-xs text-hc-muted mt-1">
            Cryptographically signed event log of all administrative, operator, and autonomous actions
          </p>
        </div>

        <div className="relative w-64">
          <input
            type="text"
            placeholder="Filter audit logs..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-hc-card border border-hc-border rounded-lg px-3 py-1.5 text-xs text-hc-text placeholder-hc-dim focus:outline-none focus:border-hc-accent"
          />
        </div>
      </div>

      <DemoBanner featureName="Immutable Audit Trail" />

      {isLoading ? (
        <LoadingState message="Loading audit trail..." />
      ) : filteredLogs.length === 0 ? (
        <EmptyState
          title="No Audit Records"
          description="Actions will automatically appear in this tamper-evident ledger."
          icon={<FileText className="w-6 h-6" />}
        />
      ) : (
        <Table columns={columns} data={filteredLogs} keyExtractor={(l) => l.id} />
      )}

      {/* Payload Modal */}
      <Modal
        isOpen={Boolean(selectedLog)}
        onClose={() => setSelectedLog(null)}
        title="Audit Event Details"
        subtitle={`Action: ${selectedLog?.action} (${selectedLog?.resource_type})`}
        maxWidth="md"
      >
        <div className="space-y-3">
          <div className="text-xs text-hc-dim font-mono space-y-1">
            <p>Actor: <span className="text-hc-text">{selectedLog?.user_email}</span></p>
            <p>Timestamp: <span className="text-hc-text">{selectedLog?.created_at}</span></p>
            <p>IP Address: <span className="text-hc-text">{selectedLog?.ip_address}</span></p>
          </div>

          <div>
            <span className="text-[10px] font-mono uppercase text-hc-dim block mb-1">
              Event Payload & Context
            </span>
            <pre className="p-3 rounded-lg bg-hc-bg border border-hc-border text-xs font-mono text-emerald-300 overflow-x-auto">
              {JSON.stringify(selectedLog?.payload || {}, null, 2)}
            </pre>
          </div>
        </div>
      </Modal>
    </div>
  )
}
