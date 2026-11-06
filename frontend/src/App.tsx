import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import { AppShell } from '@/components/layout/AppShell'
import { LoginPage } from '@/pages/auth/LoginPage'
import { RegisterPage } from '@/pages/auth/RegisterPage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { ServiceListPage } from '@/pages/services/ServiceListPage'
import { ServiceDetailPage } from '@/pages/services/ServiceDetailPage'
import { MonitoringDashboardPage } from '@/pages/monitoring/MonitoringDashboardPage'
import { IncidentListPage } from '@/pages/incidents/IncidentListPage'
import { IncidentDetailPage } from '@/pages/incidents/IncidentDetailPage'
import { RecoveryPoliciesPage } from '@/pages/recovery/RecoveryPoliciesPage'
import { ApprovalRequestsPage } from '@/pages/recovery/ApprovalRequestsPage'
import { RecoveryHistoryPage } from '@/pages/recovery/RecoveryHistoryPage'
import { AuditLogsPage } from '@/pages/audit/AuditLogsPage'
import { SettingsPage } from '@/pages/settings/SettingsPage'
import { LoadingState } from '@/components/common/Feedback'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-hc-bg">
        <LoadingState message="Initializing HealCloud SRE Console..." />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

const PublicRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-hc-bg">
        <LoadingState message="Loading..." />
      </div>
    )
  }

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <LoginPage />
                </PublicRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicRoute>
                  <RegisterPage />
                </PublicRoute>
              }
            />

            {/* Protected Routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="services" element={<ServiceListPage />} />
              <Route path="services/:id" element={<ServiceDetailPage />} />
              <Route path="monitoring" element={<MonitoringDashboardPage />} />
              <Route path="incidents" element={<IncidentListPage />} />
              <Route path="incidents/:id" element={<IncidentDetailPage />} />
              <Route path="recovery-policies" element={<RecoveryPoliciesPage />} />
              <Route path="approvals" element={<ApprovalRequestsPage />} />
              <Route path="recovery-history" element={<RecoveryHistoryPage />} />
              <Route path="audit-logs" element={<AuditLogsPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
