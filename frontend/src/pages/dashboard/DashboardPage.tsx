import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Timer,
  ShieldCheck,
  AlertOctagon,
  Cpu,
  ArrowRight,
  Server,
  Plus,
  RefreshCw,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { Service, Incident } from '@/types'
import { MetricKpiCard } from '@/components/common/Card'
import { HealthBadge, SeverityBadge, IncidentStatusBadge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { LoadingState, EmptyState } from '@/components/common/Feedback'
import { formatRelativeTime, formatLatency } from '@/utils/formatters'

export const DashboardPage: React.FC = () => {
  const { currentOrg, currentWorkspace } = useAuth()

  const [services, setServices] = useState<Service[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const loadData = async () => {
    if (!currentOrg || !currentWorkspace) return

    try {
      const [svcList, incRes] = await Promise.all([
        api.listServices(currentOrg.id, currentWorkspace.id),
        api.listIncidents(currentOrg.id, currentWorkspace.id, { size: 10 }),
      ])
      setServices(svcList)
      setIncidents(incRes.items)
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    setIsLoading(true)
    loadData()
  }, [currentOrg, currentWorkspace])

  const handleManualRefresh = () => {
    setIsRefreshing(true)
    loadData()
  }

  if (isLoading) {
    return <LoadingState message="Connecting to telemetry engine..." />
  }

  const activeIncidents = incidents.filter((i) => i.status !== 'RESOLVED' && i.status !== 'CLOSED')
  const criticalCount = activeIncidents.filter((i) => i.severity === 'P1_CRITICAL').length
  const healthyServices = services.filter((s) => s.health_status === 'HEALTHY').length
  const healthRate = services.length > 0 ? Math.round((healthyServices / services.length) * 100) : 100

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Top Bar / Greeting */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-hc-text">Operations Dashboard</h1>
          <p className="text-xs text-hc-muted mt-1">
            Real-time reliability pulse for{' '}
            <span className="font-semibold text-hc-text">{currentWorkspace?.name}</span> (
            {currentOrg?.name})
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleManualRefresh}
            isLoading={isRefreshing}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh Telemetry
          </Button>
          <Link to="/services">
            <Button size="sm" icon={<Plus className="w-3.5 h-3.5" />}>
              Register Service
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricKpiCard
          title="Mean MTTR"
          value="2m 14s"
          change="-68%"
          trend="up"
          subtitle="Autonomous RCA & Remediation"
          icon={<Timer className="w-5 h-5 text-emerald-400" />}
        />
        <MetricKpiCard
          title="Auto-Heal Rate"
          value={`${healthRate}%`}
          change={`${healthyServices}/${services.length} services`}
          trend="up"
          subtitle="Verified closed-loop resolution"
          icon={<ShieldCheck className="w-5 h-5 text-hc-accent" />}
        />
        <MetricKpiCard
          title="Active Outages"
          value={activeIncidents.length}
          change={criticalCount > 0 ? `${criticalCount} P1 Critical` : '0 Critical'}
          trend={criticalCount > 0 ? 'down' : 'neutral'}
          subtitle="Triage required in war room"
          variant={criticalCount > 0 ? 'critical' : 'default'}
          icon={<AlertOctagon className="w-5 h-5 text-hc-critical" />}
        />
        <MetricKpiCard
          title="Guardrails Status"
          value="ENFORCED"
          change="0 Tripped"
          trend="neutral"
          subtitle="Rate-limits & blast radius active"
          icon={<Cpu className="w-5 h-5 text-blue-400" />}
        />
      </div>

      {/* Active Incidents Stream Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              {activeIncidents.length > 0 && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              )}
              <span
                className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  activeIncidents.length > 0 ? 'bg-red-500' : 'bg-emerald-500'
                }`}
              ></span>
            </span>
            <h2 className="text-sm font-semibold tracking-wide uppercase text-hc-muted">
              Active Incident Stream
            </h2>
          </div>
          <Link
            to="/incidents"
            className="text-xs text-hc-accent hover:underline flex items-center gap-1 font-medium"
          >
            View All Incidents <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {activeIncidents.length === 0 ? (
          <div className="p-8 rounded-xl border border-hc-border bg-hc-card text-center">
            <ShieldCheck className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-hc-text">All Monitored Services Healthy</h3>
            <p className="text-xs text-hc-muted mt-1">
              No active P1/P2 incidents detected. All synthetic probes operating within SLAs.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {activeIncidents.map((inc) => (
              <div
                key={inc.id}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-4 rounded-xl border border-hc-border bg-hc-card hover:border-hc-borderHover transition-all gap-4 shadow-sm"
              >
                <div className="flex items-start gap-3">
                  <SeverityBadge severity={inc.severity} />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-hc-muted">
                        {inc.incident_number}
                      </span>
                      <span className="text-xs text-hc-dim">•</span>
                      <span className="text-xs font-medium text-emerald-400">
                        {inc.service_name || 'Service'}
                      </span>
                      <span className="text-xs text-hc-dim">•</span>
                      <span className="text-[11px] text-hc-dim">
                        {formatRelativeTime(inc.detected_at)}
                      </span>
                    </div>
                    <h3 className="text-sm font-medium text-hc-text mt-1">{inc.title}</h3>
                    {inc.diagnoses?.[0] && (
                      <p className="text-xs text-hc-muted mt-1">
                        <strong>Hypothesis:</strong> {inc.diagnoses[0].root_cause_hypothesis}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <IncidentStatusBadge status={inc.status} />
                  <Link to={`/incidents/${inc.id}`}>
                    <Button size="sm" variant="secondary" icon={<ArrowRight className="w-3.5 h-3.5" />}>
                      Enter War Room
                    </Button>
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Infrastructure Health Matrix */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold tracking-wide uppercase text-hc-muted">
            Monitored Services Matrix
          </h2>
          <Link
            to="/services"
            className="text-xs text-hc-accent hover:underline flex items-center gap-1 font-medium"
          >
            Manage Services ({services.length}) <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        {services.length === 0 ? (
          <EmptyState
            title="No Services Registered"
            description="Register your first microservice or HTTP endpoint to begin synthetic health monitoring and automated healing."
            actionLabel="Register Service"
            onAction={() => (window.location.href = '/services')}
            icon={<Server className="w-6 h-6" />}
          />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {services.map((svc) => (
              <Link
                key={svc.id}
                to={`/services/${svc.id}`}
                className="group flex flex-col justify-between p-4 rounded-xl border border-hc-border bg-hc-card hover:border-hc-accent/50 hover:bg-hc-cardHover transition-all shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <HealthBadge status={svc.health_status} size="sm" />
                    <span className="text-[11px] font-mono text-hc-dim">
                      {svc.endpoints?.[0]?.timeout_ms}ms SLA
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-hc-text group-hover:text-hc-accent transition-colors truncate">
                    {svc.name}
                  </h3>
                  <p className="text-xs text-hc-dim font-mono mt-1 truncate">
                    {svc.endpoints?.[0]?.url || 'No endpoint registered'}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-hc-border/60 flex items-center justify-between text-xs text-hc-muted">
                  <span>Failures: {svc.consecutive_failures}</span>
                  <span className="font-mono text-[11px]">
                    Last: {formatRelativeTime(svc.last_success_at || svc.last_failure_at)}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

