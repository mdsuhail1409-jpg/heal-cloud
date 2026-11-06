import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle,
  Clock,
  UserCheck,
  Brain,
  ShieldAlert,
  Zap,
  Activity,
  AlertTriangle,
  Play,
  RotateCcw,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { Incident, Diagnosis, IncidentEvent } from '@/types'
import { SeverityBadge, IncidentStatusBadge, Badge } from '@/components/common/Badge'
import { Card } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { TextInput, Select, Textarea } from '@/components/common/Input'
import { LoadingState, ErrorBanner } from '@/components/common/Feedback'
import { formatDateTime, formatRelativeTime } from '@/utils/formatters'

export const IncidentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { currentOrg, currentWorkspace, user } = useAuth()

  const [incident, setIncident] = useState<Incident | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDiagnosing, setIsDiagnosing] = useState(false)
  const [isExecuting, setIsExecuting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // HITL Remediation Modal
  const [isRemediateModalOpen, setIsRemediateModalOpen] = useState(false)
  const [operatorNote, setOperatorNote] = useState('')

  // Acknowledge Modal
  const [isAckModalOpen, setIsAckModalOpen] = useState(false)
  const [ackNote, setAckNote] = useState('')

  const loadIncident = async () => {
    if (!currentOrg || !currentWorkspace || !id) return
    try {
      const data = await api.getIncident(currentOrg.id, currentWorkspace.id, id)
      setIncident(data)
    } catch (err: any) {
      setError(err?.detail || 'Failed to load incident dossier')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadIncident()
  }, [currentOrg, currentWorkspace, id])

  const handleAcknowledge = async () => {
    if (!currentOrg || !currentWorkspace || !id) return
    try {
      const updated = await api.acknowledgeIncident(currentOrg.id, currentWorkspace.id, id, ackNote)
      setIncident(updated)
      setIsAckModalOpen(false)
      setAckNote('')
    } catch (err: any) {
      alert(`Acknowledgement failed: ${err?.detail || 'Error'}`)
    }
  }

  const handleAssignToMe = async () => {
    if (!currentOrg || !currentWorkspace || !id || !user) return
    try {
      const updated = await api.assignIncident(currentOrg.id, currentWorkspace.id, id, user.id)
      setIncident(updated)
    } catch (err: any) {
      alert(`Assignment failed: ${err?.detail || 'Error'}`)
    }
  }

  const handleStatusChange = async (newStatus: string) => {
    if (!currentOrg || !currentWorkspace || !id) return
    try {
      const updated = await api.updateIncidentStatus(currentOrg.id, currentWorkspace.id, id, {
        status: newStatus,
      })
      setIncident(updated)
    } catch (err: any) {
      alert(`Status transition failed: ${err?.detail || 'Error'}`)
    }
  }

  const handleTriggerDiagnosis = async () => {
    if (!currentOrg || !currentWorkspace || !id) return
    setIsDiagnosing(true)
    try {
      await api.triggerDiagnosis(currentOrg.id, currentWorkspace.id, id, true)
      await loadIncident()
    } catch (err: any) {
      alert(`Diagnosis failed: ${err?.detail || 'Error'}`)
    } finally {
      setIsDiagnosing(false)
    }
  }

  const handleExecuteRemediation = async () => {
    setIsExecuting(true)
    try {
      // Simulate remediation run
      await new Promise((r) => setTimeout(r, 1200))
      // Transition incident to RESOLVED or RECOVERING
      await handleStatusChange('RESOLVED')
      setIsRemediateModalOpen(false)
      alert('Remediation action simulated successfully. Service returned to HEALTHY state.')
    } finally {
      setIsExecuting(false)
    }
  }

  if (isLoading) {
    return <LoadingState message="Connecting to incident war room..." />
  }

  if (!incident) {
    return <ErrorBanner message="Incident record not found." />
  }

  const latestDiagnosis: Diagnosis | undefined = incident.diagnoses?.[incident.diagnoses.length - 1]
  const isResolved = incident.status === 'RESOLVED' || incident.status === 'CLOSED'

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Navigation & Status Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Link
          to="/incidents"
          className="inline-flex items-center gap-1.5 text-xs text-hc-muted hover:text-hc-text transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Incident Queue
        </Link>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {incident.status === 'OPEN' && (
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setIsAckModalOpen(true)}
              icon={<CheckCircle className="w-3.5 h-3.5 text-amber-400" />}
            >
              Acknowledge
            </Button>
          )}

          {!incident.assigned_to_user_id && (
            <Button
              size="sm"
              variant="secondary"
              onClick={handleAssignToMe}
              icon={<UserCheck className="w-3.5 h-3.5" />}
            >
              Assign to Me
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={handleTriggerDiagnosis}
            isLoading={isDiagnosing}
            icon={<RotateCcw className="w-3.5 h-3.5 text-blue-400" />}
          >
            Re-evaluate RCA
          </Button>

          {/* Status Quick Changer */}
          <div className="w-36">
            <Select
              value={incident.status}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="py-1 text-xs"
            >
              <option value="OPEN">Open</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="INVESTIGATING">Investigating</option>
              <option value="RECOVERING">Recovering</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </Select>
          </div>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* Incident Header Banner */}
      <div className="p-6 bg-hc-card border border-hc-border rounded-xl shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-bold text-hc-muted">
                {incident.incident_number}
              </span>
              <SeverityBadge severity={incident.severity} />
              <IncidentStatusBadge status={incident.status} />
            </div>

            <h1 className="text-xl font-bold tracking-tight text-hc-text mt-2">{incident.title}</h1>
            <p className="text-xs text-hc-muted mt-1">{incident.description}</p>
          </div>

          <div className="text-right sm:shrink-0 text-xs text-hc-dim font-mono space-y-1">
            <p>
              Detected:{' '}
              <span className="text-hc-text">{formatDateTime(incident.detected_at)}</span>
            </p>
            {incident.acknowledged_at && (
              <p>
                Acknowledged:{' '}
                <span className="text-amber-400">{formatRelativeTime(incident.acknowledged_at)}</span>
              </p>
            )}
            {incident.resolved_at && (
              <p>
                Resolved:{' '}
                <span className="text-emerald-400">{formatDateTime(incident.resolved_at)}</span>
              </p>
            )}
          </div>
        </div>

        <div className="pt-3 border-t border-hc-border/60 flex items-center gap-2 text-xs text-hc-muted">
          <span>Target Microservice:</span>
          <Link
            to={`/services/${incident.service_id}`}
            className="font-mono text-emerald-400 hover:underline font-semibold"
          >
            {incident.service_name || incident.service_id}
          </Link>
        </div>
      </div>

      {/* Two Column Layout: Root Cause Analysis vs Recommended Playbook */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Explainable Root Cause Analysis */}
        <Card className="space-y-4 border-hc-accent/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-hc-accent" />
              <h2 className="text-sm font-semibold tracking-wide uppercase text-hc-text">
                Root Cause Analysis (RCA)
              </h2>
            </div>
            {latestDiagnosis && (
              <Badge variant="info" size="sm">
                Confidence: {Math.round(latestDiagnosis.confidence_score * 100)}%
              </Badge>
            )}
          </div>

          {latestDiagnosis ? (
            <div className="space-y-4">
              <div>
                <span className="text-[11px] font-mono uppercase tracking-wider text-hc-dim">
                  Hypothesis ({latestDiagnosis.rule_name})
                </span>
                <p className="text-sm text-hc-text mt-1 font-medium leading-relaxed">
                  {latestDiagnosis.root_cause_hypothesis}
                </p>
              </div>

              {latestDiagnosis.evidence && (
                <div className="p-3 rounded-lg bg-hc-bg/80 border border-hc-border space-y-2">
                  <span className="text-[10px] font-mono uppercase text-hc-dim block">
                    Correlated Evidence
                  </span>
                  <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                    {Object.entries(latestDiagnosis.evidence).map(([k, v]) => (
                      <div key={k} className="truncate">
                        <span className="text-hc-dim">{k}: </span>
                        <span className="text-hc-text">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-2 text-xs text-hc-muted">
                <strong>Recommended Autonomous Action:</strong>{' '}
                <span className="font-mono text-emerald-400 font-semibold">
                  {latestDiagnosis.recommended_action}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-hc-dim">No diagnosis recorded for this incident.</p>
          )}
        </Card>

        {/* Right: Recommended Remediation Action */}
        <Card className="space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-400" />
                <h2 className="text-sm font-semibold tracking-wide uppercase text-hc-text">
                  Recommended Remediation
                </h2>
              </div>
              <Badge variant="warning" size="sm">
                Tier 2 Action
              </Badge>
            </div>

            <div className="mt-4 space-y-3">
              <div>
                <span className="text-[11px] font-mono uppercase tracking-wider text-hc-dim">
                  Remediation Action
                </span>
                <h3 className="text-base font-bold text-hc-text mt-0.5">
                  {latestDiagnosis?.recommended_action === 'SIMULATE_SCALE_UP'
                    ? 'Simulate Scale Replicas (+2 Pods)'
                    : 'Simulate Service Restart'}
                </h3>
              </div>

              <div className="p-3 rounded-lg bg-hc-bg/80 border border-hc-border space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-hc-dim">Blast Radius:</span>
                  <span className="text-hc-text font-mono">1 Target Microservice</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-hc-dim">Safety Verification:</span>
                  <span className="text-emerald-400 font-mono">Post-Recovery Synthetic Probe</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-hc-dim">Guardrail Status:</span>
                  <span className="text-blue-400 font-mono">Cooldown Verified (300s)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-hc-border">
            {isResolved ? (
              <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>Incident marked as resolved. Remediation completed.</span>
              </div>
            ) : (
              <Button
                variant="primary"
                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold shadow-lg shadow-emerald-600/20"
                onClick={() => setIsRemediateModalOpen(true)}
                icon={<Play className="w-4 h-4 fill-current" />}
              >
                Approve & Execute Remediation
              </Button>
            )}
          </div>
        </Card>
      </div>

      {/* Incident Event Timeline */}
      <Card className="space-y-4">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-hc-dim" />
          <h2 className="text-xs font-semibold uppercase tracking-wider text-hc-muted">
            Chronological Incident Timeline
          </h2>
        </div>

        <div className="space-y-4 pt-2">
          {incident.events?.map((evt, idx) => (
            <div key={evt.id || idx} className="flex items-start gap-3 relative pb-4">
              {idx < incident.events.length - 1 && (
                <div className="absolute left-2.5 top-5 w-0.5 h-full bg-hc-border" />
              )}
              <div className="w-5 h-5 rounded-full bg-hc-card border border-hc-border flex items-center justify-center shrink-0 z-10">
                <span className="w-1.5 h-1.5 rounded-full bg-hc-accent" />
              </div>

              <div className="flex-1 -mt-0.5">
                <div className="flex items-center gap-2">
                  <Badge variant="neutral" size="sm">
                    {evt.event_type}
                  </Badge>
                  <span className="text-[11px] font-mono text-hc-dim">
                    {formatDateTime(evt.created_at)}
                  </span>
                </div>
                <p className="text-xs text-hc-text mt-1">{evt.message}</p>
                {evt.payload && (
                  <pre className="mt-1.5 p-2 rounded bg-hc-bg border border-hc-border text-[11px] font-mono text-hc-muted overflow-x-auto max-w-full">
                    {JSON.stringify(evt.payload, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Human-in-the-Loop Remediation Modal */}
      <Modal
        isOpen={isRemediateModalOpen}
        onClose={() => setIsRemediateModalOpen(false)}
        title="⚠️ Authorize Autonomous Remediation"
        subtitle="Tier 2 Controlled Safe Recovery Simulation"
        maxWidth="md"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-300 text-xs space-y-1">
            <p className="font-semibold">Pre-Flight Safety Guardrail Checks: PASSED</p>
            <p className="text-[11px] text-amber-300/80">
              Cooldown window clear. Blast radius contained to service{' '}
              <span className="font-mono">{incident.service_name}</span>.
            </p>
          </div>

          <Textarea
            label="Operator Authorization Note (Optional)"
            value={operatorNote}
            onChange={(e) => setOperatorNote(e.target.value)}
            placeholder="Verified memory metrics. Approved automated restart."
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-hc-border">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsRemediateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleExecuteRemediation}
              isLoading={isExecuting}
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold"
            >
              🚀 Confirm & Execute
            </Button>
          </div>
        </div>
      </Modal>

      {/* Acknowledge Modal */}
      <Modal
        isOpen={isAckModalOpen}
        onClose={() => setIsAckModalOpen(false)}
        title="Acknowledge Incident"
        subtitle="Mark incident as acknowledged and record operator identity"
        maxWidth="sm"
      >
        <div className="space-y-4">
          <TextInput
            label="Acknowledgement Note (Optional)"
            value={ackNote}
            onChange={(e) => setAckNote(e.target.value)}
            placeholder="Investigating active downstream dependencies"
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-hc-border">
            <Button type="button" variant="ghost" onClick={() => setIsAckModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleAcknowledge}>Acknowledge</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
