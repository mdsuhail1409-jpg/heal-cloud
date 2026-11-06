import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Activity, RefreshCw, Server, AlertCircle, ArrowUpRight } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { Service, MetricSample } from '@/types'
import { Card, MetricKpiCard } from '@/components/common/Card'
import { HealthBadge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { Table, Column } from '@/components/common/Table'
import { LoadingState, EmptyState } from '@/components/common/Feedback'
import { formatDateTime, formatLatency } from '@/utils/formatters'

export const MonitoringDashboardPage: React.FC = () => {
  const { currentOrg, currentWorkspace } = useAuth()

  const [services, setServices] = useState<Service[]>([])
  const [allSamples, setAllSamples] = useState<(MetricSample & { service_name: string })[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const loadMonitoring = async () => {
    if (!currentOrg || !currentWorkspace) return
    try {
      const svcs = await api.listServices(currentOrg.id, currentWorkspace.id)
      setServices(svcs)

      // Fetch sample sets for each service
      const samplePromises = svcs.slice(0, 10).map(async (s) => {
        const samples = await api.getServiceMetricSamples(currentOrg.id, currentWorkspace.id, s.id, 10)
        return samples.map((sample) => ({ ...sample, service_name: s.name }))
      })

      const nestedSamples = await Promise.all(samplePromises)
      const flattened = nestedSamples
        .flat()
        .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

      setAllSamples(flattened)
    } catch (err) {
      console.error('Error loading monitoring data:', err)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    setIsLoading(true)
    loadMonitoring()
  }, [currentOrg, currentWorkspace])

  const handleRefresh = () => {
    setIsRefreshing(true)
    loadMonitoring()
  }

  if (isLoading) {
    return <LoadingState message="Collecting synthetic probe telemetry..." />
  }

  const healthy = services.filter((s) => s.health_status === 'HEALTHY').length
  const degraded = services.filter((s) => s.health_status === 'DEGRADED').length
  const unhealthy = services.filter((s) => s.health_status === 'UNHEALTHY').length

  const sampleColumns: Column<MetricSample & { service_name: string }>[] = [
    {
      header: 'Service',
      accessor: (s) => (
        <span className="font-semibold text-xs text-hc-text">{s.service_name}</span>
      ),
    },
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
      header: 'Probe Result',
      accessor: (s) =>
        s.is_successful ? (
          <span className="text-xs text-emerald-400 font-medium">PASS</span>
        ) : (
          <span className="text-xs text-hc-critical font-medium truncate max-w-xs block">
            FAIL ({s.error_message || 'Unresponsive'})
          </span>
        ),
    },
  ]

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-hc-text">Monitoring & Telemetry</h1>
          <p className="text-xs text-hc-muted mt-1">
            Real-time synthetic health check probes, SLA measurements, and Prometheus metrics
          </p>
        </div>

        <div className="flex items-center gap-3">
          <a
            href="/api/v1/metrics"
            target="_blank"
            rel="noreferrer"
            className="text-xs font-mono text-hc-muted hover:text-hc-accent flex items-center gap-1 border border-hc-border px-3 py-1.5 rounded-lg bg-hc-card hover:bg-hc-cardHover transition-colors"
          >
            Prometheus Metrics <ArrowUpRight className="w-3.5 h-3.5" />
          </a>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            isLoading={isRefreshing}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricKpiCard
          title="Monitored Services"
          value={services.length}
          subtitle="Configured synthetic probes"
          icon={<Server className="w-5 h-5 text-hc-accent" />}
        />
        <MetricKpiCard
          title="Healthy Services"
          value={healthy}
          trend="up"
          variant="healthy"
          subtitle="Operating within SLA bounds"
          icon={<Activity className="w-5 h-5 text-emerald-400" />}
        />
        <MetricKpiCard
          title="Degraded Services"
          value={degraded}
          trend={degraded > 0 ? 'down' : 'neutral'}
          variant={degraded > 0 ? 'warning' : 'default'}
          subtitle="1-2 consecutive check failures"
          icon={<AlertCircle className="w-5 h-5 text-amber-400" />}
        />
        <MetricKpiCard
          title="Unhealthy Outages"
          value={unhealthy}
          trend={unhealthy > 0 ? 'down' : 'neutral'}
          variant={unhealthy > 0 ? 'critical' : 'default'}
          subtitle="Crossed consecutive failure ceiling"
          icon={<AlertCircle className="w-5 h-5 text-hc-critical" />}
        />
      </div>

      {/* Unified Telemetry Stream */}
      <div className="space-y-4">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-hc-muted">
          Unified Telemetry Stream (Live Probe Samples)
        </h2>
        {allSamples.length === 0 ? (
          <EmptyState
            title="No Samples Available"
            description="Execute a probe or wait for the background worker to record synthetic samples."
            icon={<Activity className="w-6 h-6" />}
          />
        ) : (
          <Table
            columns={sampleColumns}
            data={allSamples}
            keyExtractor={(s) => `${s.id}-${s.timestamp}`}
          />
        )}
      </div>
    </div>
  )
}
