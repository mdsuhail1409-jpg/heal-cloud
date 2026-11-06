import {
  User,
  Organization,
  Workspace,
  Membership,
  Service,
  Incident,
  MetricSample,
  RecoveryPolicy,
  ApprovalRequest,
  RecoveryExecution,
  AuditLog,
  ApiError,
  Diagnosis,
} from '@/types'

const API_BASE = '/api/v1'

class ApiClient {
  private getToken(): string | null {
    return localStorage.getItem('hc_token')
  }

  public setToken(token: string) {
    localStorage.setItem('hc_token', token)
  }

  public clearToken() {
    localStorage.removeItem('hc_token')
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = this.getToken()
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    })

    if (!response.ok) {
      let errorData: ApiError
      try {
        errorData = await response.json()
      } catch {
        errorData = {
          status: response.status,
          detail: response.statusText || 'Unknown server error',
          title: 'Request Failed',
        }
      }

      // Handle 401 Unauthorized token expiry
      if (response.status === 401 && !endpoint.includes('/auth/login')) {
        this.clearToken()
        window.dispatchEvent(new Event('hc_unauthorized'))
      }

      throw errorData
    }

    // Return empty object for 204 No Content
    if (response.status === 204) {
      return {} as T
    }

    return response.json()
  }

  // --- Auth API ---
  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await this.request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    this.setToken(res.access_token)
    return res
  }

  async register(data: {
    email: string
    password: string
    full_name: string
    organization_name?: string
  }): Promise<{ access_token: string; user: User }> {
    const res = await this.request<{ access_token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    })
    this.setToken(res.access_token)
    return res
  }

  async getProfile(): Promise<{ user: User; organizations?: Organization[] }> {
    return this.request('/auth/me')
  }

  async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' })
    } finally {
      this.clearToken()
    }
  }

  // --- Organizations & Workspaces API ---
  async listOrganizations(): Promise<Organization[]> {
    return this.request('/organizations')
  }

  async createOrganization(name: string): Promise<Organization> {
    return this.request('/organizations', {
      method: 'POST',
      body: JSON.stringify({ name }),
    })
  }

  async listWorkspaces(orgId: string): Promise<Workspace[]> {
    return this.request(`/organizations/${orgId}/workspaces`)
  }

  async createWorkspace(orgId: string, name: string, description?: string): Promise<Workspace> {
    return this.request(`/organizations/${orgId}/workspaces`, {
      method: 'POST',
      body: JSON.stringify({ name, description }),
    })
  }

  async listMembers(orgId: string): Promise<Membership[]> {
    return this.request(`/organizations/${orgId}/members`)
  }

  // --- Services & Monitoring API ---
  async listServices(orgId: string, wsId: string): Promise<Service[]> {
    return this.request(`/organizations/${orgId}/workspaces/${wsId}/services`)
  }

  async getService(orgId: string, wsId: string, serviceId: string): Promise<Service> {
    return this.request(`/organizations/${orgId}/workspaces/${wsId}/services/${serviceId}`)
  }

  async createService(
    orgId: string,
    wsId: string,
    data: {
      name: string
      description?: string
      endpoint_url: string
      method?: string
      expected_status_code?: number
      timeout_ms?: number
      check_interval_seconds?: number
      consecutive_failure_threshold?: number
    }
  ): Promise<Service> {
    return this.request(`/organizations/${orgId}/workspaces/${wsId}/services`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async deleteService(orgId: string, wsId: string, serviceId: string): Promise<void> {
    return this.request(`/organizations/${orgId}/workspaces/${wsId}/services/${serviceId}`, {
      method: 'DELETE',
    })
  }

  async triggerServiceHealthCheck(
    orgId: string,
    wsId: string,
    serviceId: string
  ): Promise<{ message: string; sample: MetricSample }> {
    return this.request(
      `/organizations/${orgId}/workspaces/${wsId}/services/${serviceId}/check`,
      { method: 'POST' }
    )
  }

  async getServiceMetricSamples(
    orgId: string,
    wsId: string,
    serviceId: string,
    limit = 50
  ): Promise<MetricSample[]> {
    return this.request(
      `/organizations/${orgId}/workspaces/${wsId}/services/${serviceId}/samples?limit=${limit}`
    )
  }

  // --- Incidents & Diagnostics API ---
  async listIncidents(
    orgId: string,
    wsId: string,
    filters?: { status?: string; severity?: string; service_id?: string; page?: number; size?: number }
  ): Promise<{ items: Incident[]; total: number; page: number; size: number }> {
    const params = new URLSearchParams()
    if (filters?.status) params.append('status', filters.status)
    if (filters?.severity) params.append('severity', filters.severity)
    if (filters?.service_id) params.append('service_id', filters.service_id)
    if (filters?.page) params.append('page', filters.page.toString())
    if (filters?.size) params.append('size', filters.size.toString())

    const query = params.toString() ? `?${params.toString()}` : ''
    return this.request(`/organizations/${orgId}/workspaces/${wsId}/incidents${query}`)
  }

  async getIncident(orgId: string, wsId: string, incidentId: string): Promise<Incident> {
    return this.request(`/organizations/${orgId}/workspaces/${wsId}/incidents/${incidentId}`)
  }

  async createIncident(
    orgId: string,
    wsId: string,
    data: { service_id: string; title: string; description?: string; severity?: string }
  ): Promise<Incident> {
    return this.request(`/organizations/${orgId}/workspaces/${wsId}/incidents`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async acknowledgeIncident(
    orgId: string,
    wsId: string,
    incidentId: string,
    note?: string
  ): Promise<Incident> {
    return this.request(
      `/organizations/${orgId}/workspaces/${wsId}/incidents/${incidentId}/acknowledge`,
      {
        method: 'POST',
        body: JSON.stringify({ note }),
      }
    )
  }

  async assignIncident(
    orgId: string,
    wsId: string,
    incidentId: string,
    userId: string
  ): Promise<Incident> {
    return this.request(
      `/organizations/${orgId}/workspaces/${wsId}/incidents/${incidentId}/assign`,
      {
        method: 'POST',
        body: JSON.stringify({ assigned_to_user_id: userId }),
      }
    )
  }

  async updateIncidentStatus(
    orgId: string,
    wsId: string,
    incidentId: string,
    data: { status?: string; severity?: string; title?: string }
  ): Promise<Incident> {
    return this.request(
      `/organizations/${orgId}/workspaces/${wsId}/incidents/${incidentId}/status`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      }
    )
  }

  async triggerDiagnosis(
    orgId: string,
    wsId: string,
    incidentId: string,
    forceReEvaluation = false
  ): Promise<Diagnosis> {
    return this.request(
      `/organizations/${orgId}/workspaces/${wsId}/incidents/${incidentId}/diagnose`,
      {
        method: 'POST',
        body: JSON.stringify({ force_re_evaluation: forceReEvaluation }),
      }
    )
  }

  // --- Recovery Policies, Approvals & Audit API (With Demo Fallbacks) ---
  async listRecoveryPolicies(orgId: string, wsId: string): Promise<RecoveryPolicy[]> {
    try {
      return await this.request<RecoveryPolicy[]>(
        `/organizations/${orgId}/workspaces/${wsId}/recovery-policies`
      )
    } catch {
      // Demonstration Data clearly labeled
      return DEMO_RECOVERY_POLICIES
    }
  }

  async listApprovalRequests(orgId: string, wsId: string): Promise<ApprovalRequest[]> {
    try {
      return await this.request<ApprovalRequest[]>(
        `/organizations/${orgId}/workspaces/${wsId}/approvals`
      )
    } catch {
      return DEMO_APPROVAL_REQUESTS
    }
  }

  async decideApproval(
    _orgId: string,
    _wsId: string,
    approvalId: string,
    decision: 'APPROVED' | 'REJECTED',
    reason?: string
  ): Promise<ApprovalRequest> {
    const existing = DEMO_APPROVAL_REQUESTS.find((a) => a.id === approvalId)
    if (existing) {
      existing.status = decision
      existing.decided_at = new Date().toISOString()
      existing.decision_reason = reason
      return existing
    }
    return {
      id: approvalId,
      execution_id: 'exec-demo',
      incident_id: 'inc-demo',
      incident_number: 'INC-2026-0001',
      service_name: 'checkout-api',
      proposed_action: 'SIMULATE_RESTART',
      risk_tier: 'TIER_3_HIGH',
      blast_radius: '1 Service (3 Pods)',
      status: decision,
      requested_by: 'HealCloud Autonomous Engine',
      requested_at: new Date().toISOString(),
      decided_at: new Date().toISOString(),
      decision_reason: reason,
    }
  }

  async listRecoveryHistory(orgId: string, wsId: string): Promise<RecoveryExecution[]> {
    try {
      return await this.request<RecoveryExecution[]>(
        `/organizations/${orgId}/workspaces/${wsId}/recovery-executions`
      )
    } catch {
      return DEMO_RECOVERY_EXECUTIONS
    }
  }

  async listAuditLogs(orgId: string): Promise<AuditLog[]> {
    try {
      return await this.request<AuditLog[]>(`/organizations/${orgId}/audit-logs`)
    } catch {
      return DEMO_AUDIT_LOGS
    }
  }
}

export const api = new ApiClient()

// Demonstration preview datasets conforming to schema specifications
export const DEMO_RECOVERY_POLICIES: RecoveryPolicy[] = [
  {
    id: 'pol-01',
    organization_id: 'demo-org',
    workspace_id: 'demo-ws',
    name: 'Auto-Restart on Service Unavailability',
    trigger_condition: 'RULE_SERVICE_UNAVAILABLE',
    action: 'SIMULATE_RESTART',
    requires_approval: false,
    max_retries: 2,
    cooldown_seconds: 300,
    timeout_seconds: 60,
    is_enabled: true,
    created_at: '2026-11-06T10:00:00Z',
  },
  {
    id: 'pol-02',
    organization_id: 'demo-org',
    workspace_id: 'demo-ws',
    name: 'Scale Replicas on Severe Latency Degradation',
    trigger_condition: 'RULE_RESPONSE_TIME_EXCEEDED',
    action: 'SIMULATE_SCALE_UP',
    requires_approval: true,
    max_retries: 1,
    cooldown_seconds: 600,
    timeout_seconds: 120,
    is_enabled: true,
    created_at: '2026-11-06T10:15:00Z',
  },
  {
    id: 'pol-03',
    organization_id: 'demo-org',
    workspace_id: 'demo-ws',
    name: 'Circuit Break Downstream on Persistent 5xx Outage',
    trigger_condition: 'RULE_EXCESSIVE_CONSECUTIVE_FAILURES',
    action: 'SIMULATE_CIRCUIT_BREAK',
    requires_approval: true,
    max_retries: 1,
    cooldown_seconds: 900,
    timeout_seconds: 45,
    is_enabled: false,
    created_at: '2026-11-06T11:00:00Z',
  },
]

export const DEMO_APPROVAL_REQUESTS: ApprovalRequest[] = [
  {
    id: 'appr-01',
    execution_id: 'exec-8891',
    incident_id: 'inc-demo-1',
    incident_number: 'INC-2026-0042',
    service_name: 'payment-gateway',
    proposed_action: 'SIMULATE_SCALE_UP (+3 Pod Instances)',
    risk_tier: 'TIER_3_HIGH',
    blast_radius: '1 Kubernetes Deployment (payment-gateway-prod)',
    status: 'PENDING',
    requested_by: 'Autonomous Anomaly Policy',
    requested_at: '2026-11-06T12:20:00Z',
  },
  {
    id: 'appr-02',
    execution_id: 'exec-8892',
    incident_id: 'inc-demo-2',
    incident_number: 'INC-2026-0043',
    service_name: 'auth-cache',
    proposed_action: 'SIMULATE_FLUSH_CACHE (Invalidate token store)',
    risk_tier: 'TIER_2_MEDIUM',
    blast_radius: 'Session Store (auth-redis-cluster)',
    status: 'PENDING',
    requested_by: 'Latency Threshold Policy',
    requested_at: '2026-11-06T12:35:00Z',
  },
]

export const DEMO_RECOVERY_EXECUTIONS: RecoveryExecution[] = [
  {
    id: 'rec-01',
    incident_id: 'inc-demo-01',
    incident_number: 'INC-2026-0039',
    policy_id: 'pol-01',
    policy_name: 'Auto-Restart on Service Unavailability',
    service_name: 'checkout-api',
    action_taken: 'SIMULATE_RESTART',
    status: 'SUCCESS',
    duration_ms: 1240,
    verification_passed: true,
    started_at: '2026-11-06T11:45:00Z',
    completed_at: '2026-11-06T11:45:02Z',
  },
  {
    id: 'rec-02',
    incident_id: 'inc-demo-02',
    incident_number: 'INC-2026-0038',
    policy_id: 'pol-02',
    policy_name: 'Scale Replicas on Severe Latency Degradation',
    service_name: 'inventory-svc',
    action_taken: 'SIMULATE_SCALE_UP',
    status: 'FAILED',
    duration_ms: 5400,
    verification_passed: false,
    failure_reason: 'Health check probe returned HTTP 503 within 30s verification window.',
    started_at: '2026-11-06T10:10:00Z',
    completed_at: '2026-11-06T10:10:06Z',
  },
]

export const DEMO_AUDIT_LOGS: AuditLog[] = [
  {
    id: 'aud-01',
    organization_id: 'demo-org',
    user_email: 'sarah.sre@acme-cloud.io',
    action: 'APPROVAL_GRANTED',
    resource_type: 'ApprovalRequest',
    resource_id: 'appr-01',
    payload: { action: 'SIMULATE_SCALE_UP', note: 'Approved after checking cluster CPU ceiling' },
    ip_address: '198.51.100.42',
    created_at: '2026-11-06T12:22:00Z',
  },
  {
    id: 'aud-02',
    organization_id: 'demo-org',
    user_email: 'system.engine@healcloud.io',
    action: 'POLICY_TRIGGERED',
    resource_type: 'RecoveryPolicy',
    resource_id: 'pol-01',
    payload: { incident_number: 'INC-2026-0039', service: 'checkout-api' },
    ip_address: '10.0.4.12',
    created_at: '2026-11-06T11:45:00Z',
  },
  {
    id: 'aud-03',
    organization_id: 'demo-org',
    user_email: 'alex.lead@acme-cloud.io',
    action: 'SERVICE_REGISTERED',
    resource_type: 'Service',
    resource_id: 'srv-prod-checkout',
    payload: { name: 'checkout-api', url: 'https://api.acme.io/healthz' },
    ip_address: '198.51.100.18',
    created_at: '2026-11-06T09:12:00Z',
  },
]
