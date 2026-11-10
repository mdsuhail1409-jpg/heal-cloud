import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertOctagon, Plus, Filter, ArrowRight, ShieldCheck } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { Incident, Service } from '@/types'
import { SeverityBadge, IncidentStatusBadge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { TextInput, Select, Textarea } from '@/components/common/Input'
import { LoadingState, EmptyState, ErrorBanner } from '@/components/common/Feedback'
import { formatRelativeTime } from '@/utils/formatters'

export const IncidentListPage: React.FC = () => {
  const { currentOrg, currentWorkspace } = useAuth()
  const navigate = useNavigate()

  const [incidents, setIncidents] = useState<Incident[]>([])
  const [services, setServices] = useState<Service[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [severityFilter, setSeverityFilter] = useState<string>('')
  const [selectedIdx, setSelectedIdx] = useState<number>(0)

  // Create Incident Modal
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [serviceId, setServiceId] = useState('')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [severity, setSeverity] = useState('P2_HIGH')

  const loadIncidents = async () => {
    if (!currentOrg || !currentWorkspace) return
    setIsLoading(true)
    setError(null)
    try {
      const [incRes, svcList] = await Promise.all([
        api.listIncidents(currentOrg.id, currentWorkspace.id, {
          status: statusFilter || undefined,
          severity: severityFilter || undefined,
          size: 50,
        }),
        api.listServices(currentOrg.id, currentWorkspace.id),
      ])
      setIncidents(incRes.items)
      setServices(svcList)
      if (svcList.length > 0 && !serviceId) {
        setServiceId(svcList[0].id)
      }
    } catch (err: any) {
      setError(err?.detail || 'Failed to load incidents list')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadIncidents()
  }, [currentOrg, currentWorkspace, statusFilter, severityFilter])

  // Keyboard navigation shortcuts: 'j' down, 'k' up, 'Enter' or 'o' to open
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        document.activeElement?.tagName === 'INPUT' ||
        document.activeElement?.tagName === 'TEXTAREA' ||
        isModalOpen
      ) {
        return
      }

      if (e.key === 'j') {
        setSelectedIdx((prev) => Math.min(prev + 1, Math.max(incidents.length - 1, 0)))
      } else if (e.key === 'k') {
        setSelectedIdx((prev) => Math.max(prev - 1, 0))
      } else if ((e.key === 'Enter' || e.key === 'o') && incidents[selectedIdx]) {
        navigate(`/incidents/${incidents[selectedIdx].id}`)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [incidents, selectedIdx, isModalOpen, navigate])

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentOrg || !currentWorkspace) return
    setIsSubmitting(true)
    setError(null)

    try {
      const created = await api.createIncident(currentOrg.id, currentWorkspace.id, {
        service_id: serviceId,
        title,
        description,
        severity,
      })
      setIsModalOpen(false)
      setTitle('')
      setDescription('')
      navigate(`/incidents/${created.id}`)
    } catch (err: any) {
      setError(err?.detail || 'Failed to declare incident')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-hc-text">Incidents & RCA Queue</h1>
          <p className="text-xs text-hc-muted mt-1">
            Automated threshold detections, root-cause diagnostics, and operator triage queue
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button onClick={() => setIsModalOpen(true)} icon={<Plus className="w-4 h-4" />}>
            Declare Incident
          </Button>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl border border-hc-border bg-hc-card">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-hc-muted font-medium">
            <Filter className="w-3.5 h-3.5 text-hc-dim" /> Filter:
          </div>

          <div className="w-40">
            <Select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="py-1 text-xs"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="INVESTIGATING">Investigating</option>
              <option value="RECOVERING">Recovering</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </Select>
          </div>

          <div className="w-40">
            <Select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="py-1 text-xs"
            >
              <option value="">All Severities</option>
              <option value="P1_CRITICAL">P1 Critical</option>
              <option value="P2_HIGH">P2 High</option>
              <option value="P3_MEDIUM">P3 Medium</option>
              <option value="P4_LOW">P4 Low</option>
            </Select>
          </div>
        </div>

        <div className="text-[11px] font-mono text-hc-dim">
          <span>Tip: Press <kbd className="px-1 border border-hc-border rounded bg-hc-bg">j</kbd> / <kbd className="px-1 border border-hc-border rounded bg-hc-bg">k</kbd> to move, <kbd className="px-1 border border-hc-border rounded bg-hc-bg">o</kbd> to open war room</span>
        </div>
      </div>

      {/* Incidents List */}
      {isLoading ? (
        <LoadingState message="Fetching incident queue..." />
      ) : incidents.length === 0 ? (
        <EmptyState
          title="No Matching Incidents"
          description="No incidents match the active filters or all systems are functioning normally."
          icon={<ShieldCheck className="w-6 h-6 text-emerald-400" />}
        />
      ) : (
        <div className="space-y-3">
          {incidents.map((inc, idx) => {
            const isSelected = idx === selectedIdx
            return (
              <div
                key={inc.id}
                onClick={() => navigate(`/incidents/${inc.id}`)}
                className={`flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border bg-hc-card cursor-pointer transition-all gap-4 ${
                  isSelected
                    ? 'border-hc-accent shadow-[0_0_15px_-3px_rgba(59,130,246,0.25)] bg-hc-cardHover'
                    : 'border-hc-border hover:border-hc-borderHover'
                }`}
              >
                <div className="flex items-start gap-4">
                  <SeverityBadge severity={inc.severity} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-hc-muted">
                        {inc.incident_number}
                      </span>
                      <span className="text-xs text-hc-dim">•</span>
                      <span className="text-xs font-medium text-emerald-400">
                        {inc.service_name || 'Affected Service'}
                      </span>
                      <span className="text-xs text-hc-dim">•</span>
                      <span className="text-[11px] text-hc-dim font-mono">
                        {formatRelativeTime(inc.detected_at)}
                      </span>
                    </div>

                    <h3 className="text-sm font-semibold text-hc-text mt-1">{inc.title}</h3>

                    {inc.diagnoses?.[0] && (
                      <p className="text-xs text-hc-muted mt-1.5 flex items-center gap-1.5">
                        <span className="px-1.5 py-0.5 rounded bg-hc-border/50 text-[10px] font-mono font-semibold text-blue-300">
                          RCA {Math.round(inc.diagnoses[0].confidence_score * 100)}%
                        </span>
                        <span className="truncate max-w-lg">
                          {inc.diagnoses[0].root_cause_hypothesis}
                        </span>
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <IncidentStatusBadge status={inc.status} />
                  <Link to={`/incidents/${inc.id}`}>
                    <Button size="sm" variant="secondary" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                      War Room
                    </Button>
                  </Link>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Declare Incident Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Declare New Reliability Incident"
        subtitle="Manually record an outage and trigger explainable RCA diagnosis"
        maxWidth="md"
      >
        <form onSubmit={handleCreateIncident} className="space-y-4">
          <Select
            label="Affected Microservice"
            value={serviceId}
            onChange={(e) => setServiceId(e.target.value)}
            required
          >
            {services.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>

          <TextInput
            label="Incident Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="High error rate following deployment"
            required
          />

          <Select
            label="Severity Classification"
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            <option value="P1_CRITICAL">P1 Critical (Complete Outage)</option>
            <option value="P2_HIGH">P2 High (Degraded Performance / Flapping)</option>
            <option value="P3_MEDIUM">P3 Medium (Latency Degradation)</option>
            <option value="P4_LOW">P4 Low (Informational)</option>
          </Select>

          <Textarea
            label="Description / Observations (Optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Observed connection starvation after canary rollout."
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-hc-border">
            <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Open Incident
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

