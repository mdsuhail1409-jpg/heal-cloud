import React, { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Server,
  Play,
  Trash2,
  Activity,
  Clock,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { Service, MetricSample } from '@/types'
import { HealthBadge } from '@/components/common/Badge'
import { Card, MetricKpiCard } from '@/components/common/Card'
import { Button } from '@/components/common/Button'
import { Table, Column } from '@/components/common/Table'
import { LatencyBarChart } from '@/components/common/Charts'
import { LoadingState, ErrorBanner } from '@/components/common/Feedback'
import { formatDateTime, formatLatency } from '@/utils/formatters'

export const ServiceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const { currentOrg, currentWorkspace } = useAuth()
  const navigate = useNavigate()

  const [service, setService] = useState<Service | null>(null)
  const [samples, setSamples] = useState<MetricSample[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isProbing, setIsProbing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadService = async () => {
    if (!currentOrg || !currentWorkspace || !id) return
    try {
      const [svc, sampleList] = await Promise.all([
        api.getService(currentOrg.id, currentWorkspace.id, id),
        api.getServiceMetricSamples(currentOrg.id, currentWorkspace.id, id, 30),
      ])
      setService(svc)
      setSamples(sampleList)
    } catch (err: any) {
      setError(err?.detail || 'Failed to load service telemetry')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadService()
  }, [currentOrg, currentWorkspace, id])

  const handleManualProbe = async () => {
    if (!currentOrg || !currentWorkspace || !id) return
    setIsProbing(true)
    try {
      await api.triggerServiceHealthCheck(currentOrg.id, currentWorkspace.id, id)
      await loadService()
    } catch (err: any) {
      alert(`Probe failed: ${err?.detail || 'Error'}`)
    } finally {
      setIsProbing(false)
    }
  }

  const handleDelete = async () => {
    if (!currentOrg || !currentWorkspace || !id) return
    if (!window.confirm('Are you sure you want to delete this service?')) return
    try {
      await api.deleteService(currentOrg.id, currentWorkspace.id, id)
      navigate('/services')
    } catch (err: any) {
      alert(`Delete failed: ${err?.detail || 'Error'}`)
    }
  }

  if (isLoading) {
    return <LoadingState message="Loading service telemetry..." />
  }

  if (!service) {
    return <ErrorBanner message="Service not found or access denied." />
  }

  const ep = service.endpoints?.[0]
  const check = service.checks?.[0]

  const sampleColumns: Column<MetricSample>[] = [
    {
      header: 'Timestamp',
      accessor: (s) => (
        <span className="font-mono text-xs text-hc-dim">{formatDateTime(s.timestamp)}</span>
      ),
    },
    {
      header: 'HTTP Status',
      accessor: (s) => (
        <span
          className={`font-mono text-xs font-semibold ${
            s.is_successful ? 'text-emerald-400' : 'text-hc-critical'
          }`}
        >
          {s.status_code || 'CONN_ERR'}
        </span>
      ),
      align: 'center',
    },
    {
      header: 'Response Time',
      accessor: (s) => (
        <span className="font-mono text-xs text-hc-text">{formatLatency(s.response_time_ms)}</span>
      ),
      align: 'right',
    },
    {
      header: 'Outcome',
      accessor: (s) =>
        s.is_successful ? (
          <span className="inline-flex items-center text-xs text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Success
          </span>
        ) : (
          <span className="inline-flex items-center text-xs text-hc-critical">
            <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Failed: {s.error_message || 'Error'}
          </span>
        ),
    },
  ]

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <Link
          to="/services"
          className="inline-flex items-center gap-1.5 text-xs text-hc-muted hover:text-hc-text transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Services
        </Link>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            onClick={handleManualProbe}
            isLoading={isProbing}
            icon={<Play className="w-3.5 h-3.5 text-emerald-400" />}
          >
            Execute Probe
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={handleDelete}
            className="text-hc-critical hover:text-red-400 hover:bg-red-950/20"
            icon={<Trash2 className="w-3.5 h-3.5" />}
          >
            Delete
          </Button>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}

      {/* Service Header Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 bg-hc-card border border-hc-border rounded-xl gap-4 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-hc-border/40 text-hc-accent shrink-0">
            <Server className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold tracking-tight text-hc-text">{service.name}</h1>
              <HealthBadge status={service.health_status} />
            </div>
            <p className="text-xs text-hc-muted mt-1">{service.description || 'No description provided'}</p>
            <p className="text-xs font-mono text-hc-accent mt-2">{ep?.url}</p>
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricKpiCard
          title="Consecutive Failures"
          value={service.consecutive_failures}
          variant={service.consecutive_failures > 0 ? 'critical' : 'healthy'}
          subtitle={`Threshold: ${check?.consecutive_failure_threshold || 3} failures`}
          icon={<AlertTriangle className="w-5 h-5" />}
        />
        <MetricKpiCard
          title="Probe Interval"
          value={`${check?.interval_seconds || 30}s`}
          subtitle="Automated background schedule"
          icon={<Clock className="w-5 h-5 text-blue-400" />}
        />
        <MetricKpiCard
          title="SLA Timeout"
          value={`${ep?.timeout_ms || 3000}ms`}
          subtitle={`Expected HTTP ${ep?.expected_status_code || 200}`}
          icon={<Activity className="w-5 h-5 text-emerald-400" />}
        />
        <MetricKpiCard
          title="Samples Recorded"
          value={samples.length}
          subtitle="Telemetry snapshots"
          icon={<Server className="w-5 h-5 text-purple-400" />}
        />
      </div>

      {/* Latency Distribution Chart */}
      <Card className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-hc-muted">
            Recent Latency & Failure Telemetry
          </h2>
          <span className="text-[11px] font-mono text-hc-dim">Last 30 probes</span>
        </div>
        <LatencyBarChart samples={samples} />
      </Card>

      {/* Recent Metric Samples Table */}
      <div className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-hc-muted">
          Probe Sample History
        </h2>
        <Table columns={sampleColumns} data={samples} keyExtractor={(s) => s.id} />
      </div>
    </div>
  )
}
