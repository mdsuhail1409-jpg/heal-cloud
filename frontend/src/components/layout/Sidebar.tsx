import React from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Server,
  Activity,
  AlertOctagon,
  ShieldAlert,
  CheckSquare,
  History,
  FileText,
  Settings,
  LogOut,
  Zap,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { cn } from '@/utils/cn'

export interface SidebarProps {
  activeIncidentsCount?: number
  pendingApprovalsCount?: number
  onCloseMobile?: () => void
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeIncidentsCount = 0,
  pendingApprovalsCount = 0,
  onCloseMobile,
}) => {
  const { user, logout } = useAuth()

  const navItems = [
    { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
    { label: 'Service Inventory', to: '/services', icon: Server },
    { label: 'Monitoring', to: '/monitoring', icon: Activity },
    {
      label: 'Incidents',
      to: '/incidents',
      icon: AlertOctagon,
      badge: activeIncidentsCount > 0 ? activeIncidentsCount : undefined,
      badgeVariant: 'critical',
    },
    { label: 'Recovery Policies', to: '/recovery-policies', icon: ShieldAlert },
    {
      label: 'Approval Requests',
      to: '/approvals',
      icon: CheckSquare,
      badge: pendingApprovalsCount > 0 ? pendingApprovalsCount : undefined,
      badgeVariant: 'warning',
    },
    { label: 'Recovery History', to: '/recovery-history', icon: History },
    { label: 'Audit Logs', to: '/audit-logs', icon: FileText },
    { label: 'Settings', to: '/settings', icon: Settings },
  ]

  return (
    <aside className="w-64 bg-hc-card border-r border-hc-border flex flex-col justify-between h-screen shrink-0 z-30">
      {/* Brand Header */}
      <div>
        <div className="h-16 flex items-center px-6 border-b border-hc-border gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-hc-accent to-blue-400 flex items-center justify-center shadow-lg shadow-hc-accent/20">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-bold tracking-tight text-hc-text text-base">HealCloud</span>
            <span className="ml-1.5 px-1.5 py-0.2 text-[9px] font-mono tracking-wider bg-hc-border/60 text-hc-muted uppercase rounded">
              SaaS
            </span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onCloseMobile}
              className={({ isActive }) =>
                cn(
                  'flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all group select-none',
                  isActive
                    ? 'bg-hc-accent/15 text-white font-semibold border-l-2 border-hc-accent'
                    : 'text-hc-muted hover:text-hc-text hover:bg-hc-cardHover'
                )
              }
            >
              <div className="flex items-center gap-3">
                <item.icon className="w-4 h-4 shrink-0 transition-colors group-hover:text-hc-text" />
                <span>{item.label}</span>
              </div>
              {item.badge !== undefined && (
                <span
                  className={cn(
                    'px-1.5 py-0.5 text-[10px] font-mono font-bold rounded-full',
                    item.badgeVariant === 'critical' && 'bg-hc-critical text-white',
                    item.badgeVariant === 'warning' && 'bg-hc-warning text-black'
                  )}
                >
                  {item.badge}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Footer Profile & Logout */}
      <div className="p-4 border-t border-hc-border space-y-3">
        <div className="flex items-center gap-2 px-2 py-1">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-[11px] font-mono text-hc-muted">Engine: Active / Healthy</span>
        </div>

        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-7 h-7 rounded-full bg-hc-accent/30 border border-hc-accent/50 flex items-center justify-center text-xs font-semibold text-white uppercase shrink-0">
              {user?.full_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
            </div>
            <div className="truncate">
              <p className="text-xs font-medium text-hc-text truncate">{user?.full_name || 'Engineer'}</p>
              <p className="text-[10px] text-hc-dim truncate font-mono">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="text-hc-dim hover:text-hc-critical p-1.5 rounded-lg hover:bg-hc-border/40 transition-colors"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
