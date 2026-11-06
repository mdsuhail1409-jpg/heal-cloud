export type RoleEnum = 'ORG_OWNER' | 'ORG_ADMIN' | 'RELIABILITY_ENGINEER' | 'VIEWER'

export type HealthStatusEnum = 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | 'UNKNOWN'

export type IncidentSeverityEnum = 'P1_CRITICAL' | 'P2_HIGH' | 'P3_MEDIUM' | 'P4_LOW'

export type IncidentStatusEnum =
  | 'OPEN'
  | 'ACKNOWLEDGED'
  | 'INVESTIGATING'
  | 'RECOVERY_PENDING'
  | 'RECOVERING'
  | 'RESOLVED'
  | 'CLOSED'
  | 'FAILED'

export type IncidentEventTypeEnum =
  | 'DETECTED'
  | 'DIAGNOSED'
  | 'ACKNOWLEDGED'
  | 'ASSIGNED'
  | 'STATUS_CHANGED'
  | 'THRESHOLD_BREACHED'
  | 'RECOVERY_REQUESTED'
  | 'RECOVERY_STARTED'
  | 'RECOVERY_VERIFIED'
  | 'RECOVERY_FAILED'
  | 'RESOLVED'
  | 'NOTE_ADDED'

export interface User {
  id: string
  email: string
  full_name?: string
  is_active: boolean
  is_platform_admin: boolean
  created_at: string
  memberships?: UserMembershipInfo[]
}

export interface UserMembershipInfo {
  organization_id: string
  organization_name: string
  organization_slug: string
  role: RoleEnum
}

export interface Organization {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
}

export interface Workspace {
  id: string
  organization_id: string
  name: string
  slug: string
  description?: string
  created_at: string
}

export interface Membership {
  id: string
  organization_id: string
  user_id: string
  role: RoleEnum
  user?: User
  created_at: string
}

export interface ServiceEndpoint {
  id: string
  service_id: string
  name: string
  url: string
  method: string
  expected_status_code: number
  timeout_ms: number
  headers?: Record<string, string>
  created_at: string
}

export interface MonitoringCheck {
  id: string
  service_id: string
  endpoint_id: string
  interval_seconds: number
  consecutive_failure_threshold: number
  is_active: boolean
  last_checked_at?: string
}

export interface MetricSample {
  id: string
  check_id: string
  service_id: string
  timestamp: string
  status_code?: number | null
  response_time_ms: number
  is_successful: boolean
  error_message?: string | null
}

export interface Service {
  id: string
  organization_id: string
  workspace_id: string
  name: string
  description?: string
  health_status: HealthStatusEnum
  consecutive_failures: number
  last_success_at?: string | null
  last_failure_at?: string | null
  created_at: string
  endpoints: ServiceEndpoint[]
  checks: MonitoringCheck[]
  recent_samples?: MetricSample[]
}

export interface IncidentEvent {
  id: string
  incident_id: string
  event_type: string
  message: string
  payload?: Record<string, any>
  created_at: string
}

export interface Diagnosis {
  id: string
  incident_id: string
  rule_name: string
  root_cause_hypothesis: string
  confidence_score: number
  evidence?: Record<string, any>
  recommended_action: string
  created_at: string
}

export interface Incident {
  id: string
  organization_id: string
  workspace_id: string
  service_id: string
  incident_number: string
  title: string
  description?: string
  severity: IncidentSeverityEnum
  status: IncidentStatusEnum
  assigned_to_user_id?: string | null
  detected_at: string
  acknowledged_at?: string | null
  resolved_at?: string | null
  created_at: string
  updated_at: string
  service_name?: string
  events: IncidentEvent[]
  diagnoses: Diagnosis[]
}

export interface RecoveryPolicy {
  id: string
  organization_id: string
  workspace_id: string
  service_id?: string | null
  service_name?: string
  name: string
  trigger_condition: string
  action: 'SIMULATE_RESTART' | 'SIMULATE_SCALE_UP' | 'SIMULATE_CIRCUIT_BREAK' | 'SIMULATE_FLUSH_CACHE'
  requires_approval: boolean
  max_retries: number
  cooldown_seconds: number
  timeout_seconds: number
  is_enabled: boolean
  created_at: string
}

export interface ApprovalRequest {
  id: string
  execution_id: string
  incident_id: string
  incident_number: string
  service_name: string
  proposed_action: string
  risk_tier: 'TIER_1_LOW' | 'TIER_2_MEDIUM' | 'TIER_3_HIGH'
  blast_radius: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED'
  requested_by: string
  requested_at: string
  decided_by?: string
  decided_at?: string
  decision_reason?: string
}

export interface RecoveryExecution {
  id: string
  incident_id: string
  incident_number: string
  policy_id: string
  policy_name: string
  service_name: string
  action_taken: string
  status: 'QUEUED' | 'RUNNING' | 'VERIFYING' | 'SUCCESS' | 'FAILED' | 'ROLLED_BACK'
  duration_ms?: number
  verification_passed?: boolean
  failure_reason?: string
  operator_id?: string
  started_at: string
  completed_at?: string
}

export interface AuditLog {
  id: string
  organization_id: string
  user_email: string
  action: string
  resource_type: string
  resource_id: string
  payload?: Record<string, any>
  ip_address?: string
  created_at: string
}

export interface ApiError {
  type?: string
  title?: string
  status: number
  detail: string
  instance?: string
  timestamp?: string
}
