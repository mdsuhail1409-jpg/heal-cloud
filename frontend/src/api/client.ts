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

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL ? import.meta.env.VITE_API_BASE_URL.replace(/\/$/, '') : '') +
  '/api/v1'

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
  ): Promise<{
    service_id: string
    service_name: string
    health_status: string
    status_code: number | null
    response_time_ms: number
    consecutive_failures: number
    is_successful: boolean
    error_message: string | null
    checked_at: string
  }> {
    return this.request(
      `/organizations/${orgId}/workspaces/${wsId}/services/${serviceId}/checks/run`,
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
      `/organizations/${orgId}/workspaces/${wsId}/services/${serviceId}/metrics?limit=${limit}`
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

  // --- Recovery Policies, Approvals & Controlled Simulator API ---
  async listRecoveryPolicies(orgId: string, wsId: string): Promise<RecoveryPolicy[]> {
    return this.request<RecoveryPolicy[]>(
      `/organizations/${orgId}/workspaces/${wsId}/recovery-policies`
    )
  }

  async createRecoveryPolicy(
    orgId: string,
    wsId: string,
    data: {
      name: string
      trigger_condition: string
      action: string
      requires_approval: boolean
      max_retries?: number
      cooldown_seconds?: number
      timeout_seconds?: number
      service_id?: string
    }
  ): Promise<RecoveryPolicy> {
    return this.request<RecoveryPolicy>(
      `/organizations/${orgId}/workspaces/${wsId}/recovery-policies`,
      {
        method: 'POST',
        body: JSON.stringify(data),
      }
    )
  }

  async updateRecoveryPolicy(
    orgId: string,
    wsId: string,
    policyId: string,
    data: Partial<RecoveryPolicy>
  ): Promise<RecoveryPolicy> {
    return this.request<RecoveryPolicy>(
      `/organizations/${orgId}/workspaces/${wsId}/recovery-policies/${policyId}`,
      {
        method: 'PATCH',
        body: JSON.stringify(data),
      }
    )
  }

  async listApprovalRequests(orgId: string, wsId: string): Promise<ApprovalRequest[]> {
    return this.request<ApprovalRequest[]>(
      `/organizations/${orgId}/workspaces/${wsId}/approvals`
    )
  }

  async decideApproval(
    orgId: string,
    wsId: string,
    approvalId: string,
    decision: 'APPROVED' | 'REJECTED',
    reason?: string
  ): Promise<ApprovalRequest> {
    return this.request<ApprovalRequest>(
      `/organizations/${orgId}/workspaces/${wsId}/approvals/${approvalId}/decide`,
      {
        method: 'POST',
        body: JSON.stringify({ decision, reason }),
      }
    )
  }

  async listRecoveryHistory(orgId: string, wsId: string): Promise<RecoveryExecution[]> {
    return this.request<RecoveryExecution[]>(
      `/organizations/${orgId}/workspaces/${wsId}/recovery-executions`
    )
  }

  async executeRemediation(
    orgId: string,
    wsId: string,
    incidentId: string,
    policyId?: string,
    action?: string,
    note?: string
  ): Promise<RecoveryExecution> {
    return this.request<RecoveryExecution>(
      `/organizations/${orgId}/workspaces/${wsId}/incidents/${incidentId}/remediate`,
      {
        method: 'POST',
        body: JSON.stringify({ policy_id: policyId, action, note }),
      }
    )
  }

  async listAuditLogs(orgId: string, limit = 100): Promise<AuditLog[]> {
    return this.request<AuditLog[]>(`/organizations/${orgId}/audit-logs?limit=${limit}`)
  }
}

export const api = new ApiClient()

