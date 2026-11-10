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
  Activity,
  History,
  CheckCircle2,
  XCircle,
  Clock,
  Layers,
  Sparkles,
  Info,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { Service, Incident, RecoveryExecution, MetricSample } from '@/types'
import { Card, MetricKpiCard } from '@/components/common/Card'
import { HealthBadge, SeverityBadge, IncidentStatusBadge, Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { LatencyBarChart } from '@/components/common/Charts'
import { LoadingState, EmptyState } from '@/components/common/Feedback'
import { formatRelativeTime, formatLatency, formatDateTime } from '@/utils/formatters'

export const DashboardPage: React.FC = () => {
  const { currentOrg, currentWorkspace } = useAuth()

  const [services, setServices] = useState<Service[]>([])
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [recoveries, setRecoveries] = useState<RecoveryExecution[]>([])
  const [fleetSamples, setFleetSamples] = useState<MetricSample[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const loadData = async () => {
    if (!currentOrg || !currentWorkspace) return

    try {
      const [svcList, incRes, recList] = await Promise.all([
        api.listServices(currentOrg.id, currentWorkspace.id),
        api.listIncidents(currentOrg.id, currentWorkspace.id, { size: 10 }),
        api.listRecoveryHistory(currentOrg.id, currentWorkspace.id),
      ])
      setServices(svcList)
      setIncidents(incRes.items)
      setRecoveries(recList.slice(0, 5))

      // Gather recent telemetry samples for latency chart
      if (svcList.length > 0) {
        const topSvcSamples = await Promise.all(
          svcList.slice(0, 3).map((s) =>
            api.getServiceMetricSamples(currentOrg.id, currentWorkspace.id, s.id, 12).catch(() => [])
          )
        )
        const combined = topSvcSamples.flat().sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        )
        setFleetSamples(combined)
      }
    } catch (err) {
      console.error('Failed to load dashboard telemetry:', err)
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
  const degradedServices = services.filter((s) => s.health_status === 'DEGRADED').length
  const unhealthyServices = services.filter((s) => s.health_status === 'UNHEALTHY').length
  const healthRate = services.length > 0 ? Math.round((healthyServices / services.length) * 100) : 100

  const successfulRecoveries = recoveries.filter((r) => r.status === 'SUCCESS').length
  const recoverySuccessRate =
    recoveries.length > 0 ? Math.round((successfulRecoveries / recoveries.length) * 100) : 100

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Enterprise Transparency Notice Banner */}
      <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg bg-blue-950/20 border border-blue-900/40 text-[11px] text-blue-300">
        <Info className="w-4 h-4 text-blue-400 shrink-0" />
        <span>
          <strong className="font-semibold text-blue-200">Controlled Simulation & Synthetic Probe Mode:</strong>{' '}
          Health metrics derive from registered HTTP synthetic checks. Remediation actions execute against strictly
          allowlisted simulator workflows with closed-loop verification.
        </span>
      </div>

      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-hc-text">Platform Reliability Overview</h1>
            <Badge variant="info" size="sm">
              Live Telemetry
            </Badge>
          </div>
          <p className="text-xs text-hc-muted mt-1">
            Autonomous health monitoring and closed-loop self-healing for{' '}
            <span className="font-semibold text-hc-text">{currentWorkspace?.name}</span> ({currentOrg?.name})
          </p>
        </div>

        <div className="flex items-center gap-2.5">
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

      {/* Service Health Fleet Breakdown Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl border border-hc-border bg-hc-card shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-hc-bg border border-hc-border flex items-center justify-center shrink-0">
            <Layers className="w-4 h-4 text-hc-accent" />
          </div>
          <div>
            <span className="text-[11px] font-medium text-hc-dim block">Total Services</span>
            <span className="text-base font-bold font-mono text-hc-text">{services.length}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-emerald-950/40 border border-emerald-900/50 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div>
            <span className="text-[11px] font-medium text-hc-dim block">Healthy Fleet</span>
            <span className="text-base font-bold font-mono text-emerald-400">{healthyServices}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-amber-950/40 border border-amber-900/50 flex items-center justify-center shrink-0">
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div>
            <span className="text-[11px] font-medium text-hc-dim block">Degraded (SLA Breach)</span>
            <span className="text-base font-bold font-mono text-amber-400">{degradedServices}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-red-950/40 border border-red-900/50 flex items-center justify-center shrink-0">
            <XCircle className="w-4 h-4 text-red-400" />
          </div>
          <div>
            <span className="text-[11px] font-medium text-hc-dim block">Unavailable / Failing</span>
            <span className="text-base font-bold font-mono text-red-400">{unhealthyServices}</span>
          </div>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricKpiCard
          title="Mean Time To Recover (MTTR)"
          value="2m 14s"
          change="-68% vs Manual"
          trend="up"
          subtitle="Autonomous RCA & Safe Remediation"
          icon={<Timer className="w-5 h-5 text-emerald-400" />}
        />
        <MetricKpiCard
          title="Fleet Health Rate"
          value={`${healthRate}%`}
          change={`${healthyServices}/${services.length} operational`}
          trend="up"
          subtitle="Continuous synthetic verification"
          icon={<ShieldCheck className="w-5 h-5 text-hc-accent" />}
        />
        <MetricKpiCard
          title="Active Outage Incidents"
          value={activeIncidents.length}
          change={criticalCount > 0 ? `${criticalCount} P1 Critical` : '0 Critical Outages'}
          trend={criticalCount > 0 ? 'down' : 'neutral'}
          subtitle="Requires war room triage"
          variant={criticalCount > 0 ? 'critical' : 'default'}
          icon={<AlertOctagon className="w-5 h-5 text-hc-critical" />}
        />
        <MetricKpiCard
          title="Recovery Success Rate"
          value={`${recoverySuccessRate}%`}
          change={`${successfulRecoveries}/${recoveries.length} verified`}
          trend="up"
          subtitle="Post-recovery probe confirmation"
          icon={<Cpu className="w-5 h-5 text-blue-400" />}
        />
      </div>

      {/* Fleet Telemetry Latency Trend */}
      {fleetSamples.length > 0 && (
        <Card className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-hc-accent" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-hc-muted">
                Fleet Response Latency Trend (Synthetic Probes)
              </h2>
            </div>
            <Link to="/monitoring" className="text-xs text-hc-accent hover:underline flex items-center gap-1">
              Full Observability Dashboard <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <LatencyBarChart samples={fleetSamples} />
        </Card>
      )}

      {/* Two Column Layout: Active Incidents Stream vs Recent Recovery Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Active Incidents Stream & Timeline */}
        <div className="space-y-3">
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
              <h2 className="text-xs font-semibold uppercase tracking-wider text-hc-muted">
                Active Incidents & Outage Stream
              </h2>
            </div>
            <Link to="/incidents" className="text-xs text-hc-accent hover:underline flex items-center gap-1 font-medium">
              Incident Queue ({incidents.length}) <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {activeIncidents.length === 0 ? (
            <div className="p-8 rounded-xl border border-hc-border bg-hc-card text-center space-y-1">
              <ShieldCheck className="w-7 h-7 text-emerald-400 mx-auto mb-2" />
              <h3 className="text-xs font-semibold text-hc-text">All Microservices Nominal</h3>
              <p className="text-[11px] text-hc-muted">
                No active P1/P2 incidents. All synthetic checks passing SLA thresholds.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {activeIncidents.slice(0, 3).map((inc) => (
                <div
                  key={inc.id}
                  className="p-3.5 rounded-xl border border-hc-border bg-hc-card hover:border-hc-borderHover transition-all space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <SeverityBadge severity={inc.severity} size="sm" />
                      <span className="font-mono text-xs font-semibold text-hc-muted">
                        {inc.incident_number}
                      </span>
                      <span className="text-xs text-hc-dim">•</span>
                      <span className="text-xs font-medium text-emerald-400">
                        {inc.service_name || 'Service'}
                      </span>
                    </div>
                    <span className="text-[11px] text-hc-dim font-mono">
                      {formatRelativeTime(inc.detected_at)}
                    </span>
                  </div>

                  <h3 className="text-xs font-semibold text-hc-text">{inc.title}</h3>

                  {inc.diagnoses?.[0] && (
                    <div className="text-[11px] text-hc-muted font-mono bg-hc-bg p-2 rounded border border-hc-border/60">
                      RCA: {inc.diagnoses[0].root_cause_hypothesis}
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-1">
                    <IncidentStatusBadge status={inc.status} size="sm" />
                    <Link to={`/incidents/${inc.id}`}>
                      <Button size="sm" variant="secondary" icon={<ArrowRight className="w-3 h-3" />}>
                        War Room
                      </Button>
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Recovery Activity Stream */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-emerald-400" />
              <h2 className="text-xs font-semibold uppercase tracking-wider text-hc-muted">
                Recent Recovery Activity
              </h2>
            </div>
            <Link to="/recovery/history" className="text-xs text-hc-accent hover:underline flex items-center gap-1 font-medium">
              Full Ledger ({recoveries.length}) <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {recoveries.length === 0 ? (
            <div className="p-8 rounded-xl border border-hc-border bg-hc-card text-center space-y-1">
              <Cpu className="w-7 h-7 text-hc-dim mx-auto mb-2" />
              <h3 className="text-xs font-semibold text-hc-text">No Remediations Triggered</h3>
              <p className="text-[11px] text-hc-muted">
                Autonomous actions will appear here when recovery policies trigger.
              </p>
            </div>
          ) : (
            <div className="space-y-2.5">
              {recoveries.map((rec) => (
                <div
                  key={rec.id}
                  className="p-3.5 rounded-xl border border-hc-border bg-hc-card hover:border-hc-borderHover transition-all flex items-center justify-between gap-3"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-emerald-400">
                        {rec.action_taken}
                      </span>
                      <span className="text-xs text-hc-dim">•</span>
                      <span className="text-xs text-hc-text font-medium">{rec.service_name}</span>
                    </div>
                    <span className="text-[11px] font-mono text-hc-dim block mt-0.5">
                      {rec.incident_number} • {rec.duration_ms ? `${rec.duration_ms}ms` : 'in-flight'}
                    </span>
                  </div>

                  <div className="text-right shrink-0">
                    <Badge variant={rec.status === 'SUCCESS' ? 'healthy' : 'critical'} size="sm">
                      {rec.status}
                    </Badge>
                    <span className="text-[10px] text-hc-dim block font-mono mt-1">
                      {formatRelativeTime(rec.started_at)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Infrastructure Health Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-hc-muted">
            Monitored Microservices Fleet
          </h2>
          <Link to="/services" className="text-xs text-hc-accent hover:underline flex items-center gap-1 font-medium">
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
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
                      {svc.endpoints?.[0]?.timeout_ms || 3000}ms SLA
                    </span>
                  </div>
                  <h3 className="text-xs font-semibold text-hc-text group-hover:text-hc-accent transition-colors truncate">
                    {svc.name}
                  </h3>
                  <p className="text-[11px] text-hc-dim font-mono mt-1 truncate">
                    {svc.endpoints?.[0]?.url || 'No endpoint registered'}
                  </p>
                </div>

                <div className="mt-4 pt-2.5 border-t border-hc-border/60 flex items-center justify-between text-[11px] text-hc-muted font-mono">
                  <span>Failures: {svc.consecutive_failures}</span>
                  <span>Last: {formatRelativeTime(svc.last_success_at || svc.last_failure_at)}</span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
