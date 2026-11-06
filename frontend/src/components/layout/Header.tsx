import React, { useState } from 'react'
import {
  Layers,
  ChevronDown,
  Building2,
  Menu,
  Activity,
  Keyboard,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { SearchInput } from '@/components/common/Input'

export interface HeaderProps {
  onToggleMobileMenu?: () => void
  onOpenShortcuts?: () => void
}

export const Header: React.FC<HeaderProps> = ({
  onToggleMobileMenu,
  onOpenShortcuts,
}) => {
  const { organizations, currentOrg, setCurrentOrg, workspaces, currentWorkspace, setCurrentWorkspace } =
    useAuth()

  const [showOrgDropdown, setShowOrgDropdown] = useState(false)
  const [showWsDropdown, setShowWsDropdown] = useState(false)

  return (
    <header className="h-16 bg-hc-card/60 backdrop-blur-md border-b border-hc-border px-6 flex items-center justify-between shrink-0 sticky top-0 z-20">
      {/* Left: Mobile Toggle & Workspace Switcher */}
      <div className="flex items-center gap-4">
        {onToggleMobileMenu && (
          <button
            onClick={onToggleMobileMenu}
            className="md:hidden text-hc-muted hover:text-hc-text p-1.5 rounded-lg border border-hc-border"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Organization Dropdown */}
        <div className="relative">
          <button
            onClick={() => {
              setShowOrgDropdown(!showOrgDropdown)
              setShowWsDropdown(false)
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-hc-bg/80 border border-hc-border hover:border-hc-borderHover text-xs font-medium text-hc-text transition-colors select-none"
          >
            <Building2 className="w-3.5 h-3.5 text-hc-accent shrink-0" />
            <span className="max-w-[120px] truncate">{currentOrg?.name || 'Select Org'}</span>
            <ChevronDown className="w-3 h-3 text-hc-dim" />
          </button>

          {showOrgDropdown && (
            <div className="absolute left-0 mt-1.5 w-48 bg-hc-card border border-hc-border rounded-xl shadow-modal py-1.5 z-40 animate-in fade-in zoom-in-95">
              <div className="px-3 py-1 text-[10px] font-mono uppercase text-hc-dim">Organizations</div>
              {organizations.map((org) => (
                <button
                  key={org.id}
                  onClick={() => {
                    setCurrentOrg(org)
                    setShowOrgDropdown(false)
                  }}
                  className="w-full text-left px-3 py-1.5 text-xs text-hc-text hover:bg-hc-cardHover flex items-center justify-between"
                >
                  <span className="truncate">{org.name}</span>
                  {currentOrg?.id === org.id && <span className="w-1.5 h-1.5 rounded-full bg-hc-accent" />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Workspace Dropdown */}
        <div className="relative">
          <button
            onClick={() => {
              setShowWsDropdown(!showWsDropdown)
              setShowOrgDropdown(false)
            }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-hc-bg/80 border border-hc-border hover:border-hc-borderHover text-xs font-medium text-hc-text transition-colors select-none"
          >
            <Layers className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="max-w-[130px] truncate">{currentWorkspace?.name || 'Default Workspace'}</span>
            <ChevronDown className="w-3 h-3 text-hc-dim" />
          </button>

          {showWsDropdown && (
            <div className="absolute left-0 mt-1.5 w-52 bg-hc-card border border-hc-border rounded-xl shadow-modal py-1.5 z-40 animate-in fade-in zoom-in-95">
              <div className="px-3 py-1 text-[10px] font-mono uppercase text-hc-dim">Workspaces</div>
              {workspaces.length === 0 ? (
                <div className="px-3 py-2 text-xs text-hc-dim">No workspaces</div>
              ) : (
                workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      setCurrentWorkspace(ws)
                      setShowWsDropdown(false)
                    }}
                    className="w-full text-left px-3 py-1.5 text-xs text-hc-text hover:bg-hc-cardHover flex items-center justify-between"
                  >
                    <span className="truncate">{ws.name}</span>
                    {currentWorkspace?.id === ws.id && (
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    )}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Center / Right: Global Search & Shortcuts */}
      <div className="flex items-center gap-4">
        <div className="hidden lg:block w-72">
          <SearchInput />
        </div>

        {/* Global Health Indicator */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/40 border border-emerald-800/40 text-emerald-400 text-xs font-mono">
          <Activity className="w-3.5 h-3.5 animate-pulse" />
          <span>Global Health: 99.8%</span>
        </div>

        {/* Keyboard Shortcuts Trigger */}
        {onOpenShortcuts && (
          <button
            onClick={onOpenShortcuts}
            className="text-hc-dim hover:text-hc-text p-1.5 rounded-lg hover:bg-hc-border/40 transition-colors"
            title="Keyboard shortcuts (?)"
            aria-label="Keyboard shortcuts"
          >
            <Keyboard className="w-4 h-4" />
          </button>
        )}
      </div>
    </header>
  )
}
