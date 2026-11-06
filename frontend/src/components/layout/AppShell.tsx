import React, { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { Modal } from '@/components/common/Modal'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'

export const AppShell: React.FC = () => {
  const { currentOrg, currentWorkspace } = useAuth()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [shortcutsModalOpen, setShortcutsModalOpen] = useState(false)
  const [activeIncidentsCount, setActiveIncidentsCount] = useState(0)
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState(0)

  // Fetch active counts for badges
  useEffect(() => {
    if (!currentOrg || !currentWorkspace) return

    const loadCounts = async () => {
      try {
        const incRes = await api.listIncidents(currentOrg.id, currentWorkspace.id, {
          status: 'OPEN',
        })
        setActiveIncidentsCount(incRes.total)
      } catch {
        setActiveIncidentsCount(0)
      }

      try {
        const apprRes = await api.listApprovalRequests(currentOrg.id, currentWorkspace.id)
        setPendingApprovalsCount(apprRes.filter((a) => a.status === 'PENDING').length)
      } catch {
        setPendingApprovalsCount(0)
      }
    }

    loadCounts()
    const interval = setInterval(loadCounts, 15000)
    return () => clearInterval(interval)
  }, [currentOrg, currentWorkspace])

  // Global '?' shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (
        e.key === '?' &&
        document.activeElement?.tagName !== 'INPUT' &&
        document.activeElement?.tagName !== 'TEXTAREA'
      ) {
        setShortcutsModalOpen(true)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-hc-bg">
      {/* Desktop Sidebar */}
      <div className="hidden md:flex">
        <Sidebar
          activeIncidentsCount={activeIncidentsCount}
          pendingApprovalsCount={pendingApprovalsCount}
        />
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="relative flex flex-col w-64 h-full bg-hc-card z-10 shadow-modal">
            <Sidebar
              activeIncidentsCount={activeIncidentsCount}
              pendingApprovalsCount={pendingApprovalsCount}
              onCloseMobile={() => setMobileMenuOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Main View Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <Header
          onToggleMobileMenu={() => setMobileMenuOpen(true)}
          onOpenShortcuts={() => setShortcutsModalOpen(true)}
        />
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <Outlet />
        </main>
      </div>

      {/* Keyboard Shortcuts Cheat-Sheet Modal */}
      <Modal
        isOpen={shortcutsModalOpen}
        onClose={() => setShortcutsModalOpen(false)}
        title="SRE Console Keyboard Shortcuts"
        subtitle="Accelerated keyboard triage under high operational stress"
        maxWidth="md"
      >
        <div className="space-y-4">
          <table className="w-full text-xs">
            <tbody className="divide-y divide-hc-border">
              <tr>
                <td className="py-2 text-hc-muted font-medium">Global Search</td>
                <td className="py-2 text-right">
                  <kbd className="px-2 py-1 bg-hc-bg border border-hc-border rounded font-mono text-hc-text">
                    /
                  </kbd>
                </td>
              </tr>
              <tr>
                <td className="py-2 text-hc-muted font-medium">Navigate Incidents Down / Up</td>
                <td className="py-2 text-right">
                  <kbd className="px-2 py-1 bg-hc-bg border border-hc-border rounded font-mono text-hc-text mr-1">
                    j
                  </kbd>
                  <kbd className="px-2 py-1 bg-hc-bg border border-hc-border rounded font-mono text-hc-text">
                    k
                  </kbd>
                </td>
              </tr>
              <tr>
                <td className="py-2 text-hc-muted font-medium">Open Incident War Room</td>
                <td className="py-2 text-right">
                  <kbd className="px-2 py-1 bg-hc-bg border border-hc-border rounded font-mono text-hc-text mr-1">
                    Enter
                  </kbd>
                  <span className="text-hc-dim">or</span>
                  <kbd className="px-2 py-1 bg-hc-bg border border-hc-border rounded font-mono text-hc-text ml-1">
                    o
                  </kbd>
                </td>
              </tr>
              <tr>
                <td className="py-2 text-hc-muted font-medium">Authorize HITL Remediation</td>
                <td className="py-2 text-right">
                  <kbd className="px-2 py-1 bg-hc-bg border border-hc-border rounded font-mono text-hc-text">
                    Shift + Enter
                  </kbd>
                </td>
              </tr>
              <tr>
                <td className="py-2 text-hc-muted font-medium">Dismiss Modal / Dialog</td>
                <td className="py-2 text-right">
                  <kbd className="px-2 py-1 bg-hc-bg border border-hc-border rounded font-mono text-hc-text">
                    Esc
                  </kbd>
                </td>
              </tr>
              <tr>
                <td className="py-2 text-hc-muted font-medium">Show This Help Menu</td>
                <td className="py-2 text-right">
                  <kbd className="px-2 py-1 bg-hc-bg border border-hc-border rounded font-mono text-hc-text">
                    ?
                  </kbd>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Modal>
    </div>
  )
}
