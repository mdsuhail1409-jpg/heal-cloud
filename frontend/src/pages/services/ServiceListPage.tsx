import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Server, Activity, Trash2, ArrowUpRight, Play } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { Service } from '@/types'
import { Table, Column } from '@/components/common/Table'
import { HealthBadge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { TextInput, Select } from '@/components/common/Input'
import { EmptyState, LoadingState, ErrorBanner } from '@/components/common/Feedback'
import { formatRelativeTime } from '@/utils/formatters'

export const ServiceListPage: React.FC = () => {
  const { currentOrg, currentWorkspace } = useAuth()

  const [services, setServices] = useState<Service[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [probingServiceId, setProbingServiceId] = useState<string | null>(null)

  // Registration form fields
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [endpointUrl, setEndpointUrl] = useState('')
  const [method, setMethod] = useState('GET')
  const [expectedStatusCode, setExpectedStatusCode] = useState(200)
  const [timeoutMs, setTimeoutMs] = useState(3000)
  const [checkIntervalSeconds, setCheckIntervalSeconds] = useState(30)
  const [consecutiveFailureThreshold, setConsecutiveFailureThreshold] = useState(3)

  const loadServices = async () => {
    if (!currentOrg || !currentWorkspace) return
    setIsLoading(true)
    setError(null)
    try {
      const data = await api.listServices(currentOrg.id, currentWorkspace.id)
      setServices(data)
    } catch (err: any) {
      setError(err?.detail || 'Failed to retrieve registered services')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadServices()
  }, [currentOrg, currentWorkspace])

  const handleRegisterService = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentOrg || !currentWorkspace) return
    setIsSubmitting(true)
    setError(null)

    try {
      await api.createService(currentOrg.id, currentWorkspace.id, {
        name,
        description,
        endpoint_url: endpointUrl,
        method,
        expected_status_code: expectedStatusCode,
        timeout_ms: timeoutMs,
        check_interval_seconds: checkIntervalSeconds,
        consecutive_failure_threshold: consecutiveFailureThreshold,
      })
      setIsModalOpen(false)
      // Reset form
      setName('')
      setDescription('')
      setEndpointUrl('')
      loadServices()
    } catch (err: any) {
      setError(err?.detail || 'Service registration failed. Verify target URL passes SSRF guardrails.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleManualProbe = async (svc: Service) => {
    if (!currentOrg || !currentWorkspace) return
    setProbingServiceId(svc.id)
    try {
      await api.triggerServiceHealthCheck(currentOrg.id, currentWorkspace.id, svc.id)
      loadServices()
    } catch (err: any) {
      alert(`Probe failed: ${err?.detail || 'Error'}`)
    } finally {
      setProbingServiceId(null)
    }
  }

  const handleDeleteService = async (serviceId: string) => {
    if (!currentOrg || !currentWorkspace) return
    if (!window.confirm('Are you sure you want to delete this service and its monitoring checks?'))
      return

    try {
      await api.deleteService(currentOrg.id, currentWorkspace.id, serviceId)
      setServices(services.filter((s) => s.id !== serviceId))
    } catch (err: any) {
      alert(`Failed to delete service: ${err?.detail || 'Error'}`)
    }
  }

  const columns: Column<Service>[] = [
    {
      header: 'Service Name',
      accessor: (s) => (
        <div className="flex flex-col">
          <Link
            to={`/services/${s.id}`}
            className="font-medium text-hc-text hover:text-hc-accent transition-colors flex items-center gap-1.5"
          >
            {s.name} <ArrowUpRight className="w-3 h-3 text-hc-dim" />
          </Link>
          <span className="text-[11px] text-hc-dim truncate max-w-xs">{s.description || '—'}</span>
        </div>
      ),
    },
    {
      header: 'Target Endpoint',
      accessor: (s) => (
        <span className="font-mono text-xs text-hc-muted truncate max-w-[200px] block">
          {s.endpoints?.[0]?.url || '—'}
        </span>
      ),
    },
    {
      header: 'Status',
      accessor: (s) => <HealthBadge status={s.health_status} size="sm" />,
    },
    {
      header: 'Failures',
      accessor: (s) => (
        <span
          className={`font-mono text-xs font-semibold ${
            s.consecutive_failures > 0 ? 'text-hc-critical' : 'text-hc-muted'
          }`}
        >
          {s.consecutive_failures}
        </span>
      ),
      align: 'center',
    },
    {
      header: 'Interval',
      accessor: (s) => (
        <span className="font-mono text-xs text-hc-dim">
          {s.checks?.[0]?.interval_seconds ? `${s.checks[0].interval_seconds}s` : '—'}
        </span>
      ),
      align: 'center',
    },
    {
      header: 'Last Checked',
      accessor: (s) => (
        <span className="font-mono text-[11px] text-hc-dim">
          {formatRelativeTime(s.last_success_at || s.last_failure_at)}
        </span>
      ),
    },
    {
      header: 'Actions',
      accessor: (s) => (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="ghost"
            onClick={(e) => {
              e.stopPropagation()
              handleManualProbe(s)
            }}
            isLoading={probingServiceId === s.id}
            title="Execute immediate synthetic probe"
            icon={<Play className="w-3 h-3 text-emerald-400" />}
          >
            Probe
          </Button>
          <button
            onClick={(e) => {
              e.stopPropagation()
              handleDeleteService(s.id)
            }}
            className="text-hc-dim hover:text-hc-critical p-1 rounded hover:bg-hc-border/40 transition-colors"
            title="Delete service"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      ),
      align: 'right',
    },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-hc-text">Service Inventory</h1>
          <p className="text-xs text-hc-muted mt-1">
            Registered microservices, synthetic probes, and health checkpoints
          </p>
        </div>

        <Button onClick={() => setIsModalOpen(true)} icon={<Plus className="w-4 h-4" />}>
          Register Microservice
        </Button>
      </div>

      {error && <ErrorBanner message={error} className="mb-4" />}

      {/* Services Table */}
      {isLoading ? (
        <LoadingState message="Fetching service inventory..." />
      ) : services.length === 0 ? (
        <EmptyState
          title="No Services in Workspace"
          description="Register your microservices with HTTP endpoints to monitor reliability and trigger automatic remediation."
          actionLabel="Register First Service"
          onAction={() => setIsModalOpen(true)}
          icon={<Server className="w-6 h-6" />}
        />
      ) : (
        <Table
          columns={columns}
          data={services}
          keyExtractor={(s) => s.id}
        />
      )}

      {/* Register Service Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Register New Microservice"
        subtitle="Configure synthetic health probe with SSRF protection"
        maxWidth="lg"
      >
        <form onSubmit={handleRegisterService} className="space-y-4">
          <TextInput
            label="Service Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="checkout-api"
            required
          />

          <TextInput
            label="Description (Optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Core transaction processing backend"
          />

          <TextInput
            label="Target Health Endpoint URL"
            value={endpointUrl}
            onChange={(e) => setEndpointUrl(e.target.value)}
            placeholder="https://api.acme-cloud.io/healthz"
            helperText="Public, approved domains only. Loopback, RFC 1918 private IPs, and cloud metadata (169.254.169.254) are strictly blocked."
            required
          />

          <div className="grid grid-cols-2 gap-4">
            <Select
              label="HTTP Method"
              value={method}
              onChange={(e) => setMethod(e.target.value)}
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="HEAD">HEAD</option>
            </Select>

            <TextInput
              label="Expected HTTP Status Code"
              type="number"
              value={expectedStatusCode}
              onChange={(e) => setExpectedStatusCode(parseInt(e.target.value))}
              required
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <TextInput
              label="Timeout (ms)"
              type="number"
              value={timeoutMs}
              onChange={(e) => setTimeoutMs(parseInt(e.target.value))}
              required
            />

            <TextInput
              label="Check Interval (sec)"
              type="number"
              value={checkIntervalSeconds}
              onChange={(e) => setCheckIntervalSeconds(parseInt(e.target.value))}
              required
            />

            <TextInput
              label="Failure Threshold"
              type="number"
              value={consecutiveFailureThreshold}
              onChange={(e) => setConsecutiveFailureThreshold(parseInt(e.target.value))}
              helperText="Failures to trigger P2 Incident"
              required
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-hc-border">
            <Button
              type="button"
              variant="ghost"
              onClick={() => setIsModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Register & Begin Probing
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

