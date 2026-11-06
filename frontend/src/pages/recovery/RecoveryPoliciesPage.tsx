import React, { useState, useEffect } from 'react'
import { ShieldAlert, Plus, ShieldCheck, ToggleLeft, ToggleRight } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { RecoveryPolicy } from '@/types'
import { Table, Column } from '@/components/common/Table'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { TextInput, Select } from '@/components/common/Input'
import { DemoBanner, LoadingState } from '@/components/common/Feedback'

export const RecoveryPoliciesPage: React.FC = () => {
  const { currentOrg, currentWorkspace } = useAuth()

  const [policies, setPolicies] = useState<RecoveryPolicy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Policy form fields
  const [name, setName] = useState('')
  const [triggerCondition, setTriggerCondition] = useState('RULE_SERVICE_UNAVAILABLE')
  const [action, setAction] = useState<'SIMULATE_RESTART' | 'SIMULATE_SCALE_UP' | 'SIMULATE_CIRCUIT_BREAK' | 'SIMULATE_FLUSH_CACHE'>('SIMULATE_RESTART')
  const [requiresApproval, setRequiresApproval] = useState(false)
  const [cooldownSeconds, setCooldownSeconds] = useState(300)
  const [maxRetries, setMaxRetries] = useState(2)

  const loadPolicies = async () => {
    if (!currentOrg || !currentWorkspace) return
    setIsLoading(true)
    try {
      const data = await api.listRecoveryPolicies(currentOrg.id, currentWorkspace.id)
      setPolicies(data)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadPolicies()
  }, [currentOrg, currentWorkspace])

  const handleTogglePolicy = (policyId: string) => {
    setPolicies(
      policies.map((p) => (p.id === policyId ? { ...p, is_enabled: !p.is_enabled } : p))
    )
  }

  const handleCreatePolicy = (e: React.FormEvent) => {
    e.preventDefault()
    const newPolicy: RecoveryPolicy = {
      id: `pol-${Date.now()}`,
      organization_id: currentOrg?.id || 'org',
      workspace_id: currentWorkspace?.id || 'ws',
      name,
      trigger_condition: triggerCondition,
      action,
      requires_approval: requiresApproval,
      max_retries: maxRetries,
      cooldown_seconds: cooldownSeconds,
      timeout_seconds: 60,
      is_enabled: true,
      created_at: new Date().toISOString(),
    }
    setPolicies([newPolicy, ...policies])
    setIsModalOpen(false)
    setName('')
  }

  const columns: Column<RecoveryPolicy>[] = [
    {
      header: 'Policy Name',
      accessor: (p) => (
        <div>
          <span className="font-semibold text-xs text-hc-text">{p.name}</span>
          <span className="text-[11px] font-mono text-hc-dim block mt-0.5">
            Trigger: {p.trigger_condition}
          </span>
        </div>
      ),
    },
    {
      header: 'Allowlisted Action',
      accessor: (p) => (
        <span className="font-mono text-xs font-semibold text-emerald-400">{p.action}</span>
      ),
    },
    {
      header: 'HITL Approval',
      accessor: (p) => (
        <Badge variant={p.requires_approval ? 'warning' : 'neutral'} size="sm">
          {p.requires_approval ? 'Required' : 'Autonomous'}
        </Badge>
      ),
      align: 'center',
    },
    {
      header: 'Cooldown / Retries',
      accessor: (p) => (
        <span className="font-mono text-xs text-hc-muted">
          {p.cooldown_seconds}s / max {p.max_retries}
        </span>
      ),
      align: 'center',
    },
    {
      header: 'Status',
      accessor: (p) => (
        <button
          onClick={() => handleTogglePolicy(p.id)}
          className="flex items-center gap-1 text-xs font-medium"
        >
          {p.is_enabled ? (
            <span className="inline-flex items-center text-emerald-400">
              <ToggleRight className="w-5 h-5 mr-1" /> Active
            </span>
          ) : (
            <span className="inline-flex items-center text-hc-dim">
              <ToggleLeft className="w-5 h-5 mr-1" /> Disabled
            </span>
          )}
        </button>
      ),
      align: 'center',
    },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-hc-text">Recovery Policies</h1>
          <p className="text-xs text-hc-muted mt-1">
            Allowlisted autonomous remediation actions, blast radius controls, and safety gates
          </p>
        </div>

        <Button onClick={() => setIsModalOpen(true)} icon={<Plus className="w-4 h-4" />}>
          Create Policy
        </Button>
      </div>

      <DemoBanner featureName="Recovery Policy Simulator" />

      {isLoading ? (
        <LoadingState message="Loading recovery policies..." />
      ) : (
        <Table columns={columns} data={policies} keyExtractor={(p) => p.id} />
      )}

      {/* Create Policy Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create Safe Recovery Policy"
        subtitle="Enforce allowlisted actions with strict cooldowns and retry ceilings"
        maxWidth="md"
      >
        <form onSubmit={handleCreatePolicy} className="space-y-4">
          <TextInput
            label="Policy Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Auto-Restart on Service Unavailability"
            required
          />

          <Select
            label="Trigger Condition"
            value={triggerCondition}
            onChange={(e) => setTriggerCondition(e.target.value)}
          >
            <option value="RULE_SERVICE_UNAVAILABLE">RULE_SERVICE_UNAVAILABLE</option>
            <option value="RULE_REPEATED_HEALTH_CHECK_FAILURE">
              RULE_REPEATED_HEALTH_CHECK_FAILURE
            </option>
            <option value="RULE_RESPONSE_TIME_EXCEEDED">RULE_RESPONSE_TIME_EXCEEDED</option>
            <option value="RULE_EXCESSIVE_CONSECUTIVE_FAILURES">
              RULE_EXCESSIVE_CONSECUTIVE_FAILURES
            </option>
          </Select>

          <Select
            label="Allowlisted Recovery Action"
            value={action}
            onChange={(e) => setAction(e.target.value as any)}
          >
            <option value="SIMULATE_RESTART">SIMULATE_RESTART (Restart target container/pod)</option>
            <option value="SIMULATE_SCALE_UP">SIMULATE_SCALE_UP (Add +2 replica instances)</option>
            <option value="SIMULATE_CIRCUIT_BREAK">SIMULATE_CIRCUIT_BREAK (Trip circuit breaker)</option>
            <option value="SIMULATE_FLUSH_CACHE">SIMULATE_FLUSH_CACHE (Flush stale cache keys)</option>
          </Select>

          <div className="grid grid-cols-2 gap-4">
            <TextInput
              label="Cooldown Window (seconds)"
              type="number"
              value={cooldownSeconds}
              onChange={(e) => setCooldownSeconds(parseInt(e.target.value))}
              helperText="Enforces delay between actions"
              required
            />

            <TextInput
              label="Max Retries"
              type="number"
              value={maxRetries}
              onChange={(e) => setMaxRetries(parseInt(e.target.value))}
              helperText="Maximum attempts before failure"
              required
            />
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="reqApproval"
              checked={requiresApproval}
              onChange={(e) => setRequiresApproval(e.target.checked)}
              className="rounded border-hc-border bg-hc-card text-hc-accent focus:ring-hc-accent"
            />
            <label htmlFor="reqApproval" className="text-xs text-hc-text select-none">
              Require Human-in-the-Loop (HITL) cryptographic approval before execution
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-hc-border">
            <Button type="button" variant="ghost" onClick={() => setIsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit">Create Policy</Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
