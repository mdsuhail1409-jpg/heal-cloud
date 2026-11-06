import React, { useState, useEffect } from 'react'
import { Settings, User, Building, Layers, Users, Key, Plus } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { api } from '@/api/client'
import { Membership } from '@/types'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'
import { Button } from '@/components/common/Button'
import { Modal } from '@/components/common/Modal'
import { TextInput, Select } from '@/components/common/Input'
import { Table, Column } from '@/components/common/Table'
import { formatDateTime } from '@/utils/formatters'

export const SettingsPage: React.FC = () => {
  const { user, currentOrg, workspaces, currentWorkspace, setCurrentWorkspace, refreshWorkspaces } =
    useAuth()

  const [activeTab, setActiveTab] = useState<'profile' | 'organization' | 'workspaces' | 'members'>('profile')
  const [members, setMembers] = useState<Membership[]>([])
  const [isLoadingMembers, setIsLoadingMembers] = useState(false)

  // Create Workspace Modal
  const [isWsModalOpen, setIsWsModalOpen] = useState(false)
  const [wsName, setWsName] = useState('')
  const [wsDesc, setWsDesc] = useState('')
  const [isSubmittingWs, setIsSubmittingWs] = useState(false)

  useEffect(() => {
    if (activeTab === 'members' && currentOrg) {
      setIsLoadingMembers(true)
      api
        .listMembers(currentOrg.id)
        .then(setMembers)
        .catch(console.error)
        .finally(() => setIsLoadingMembers(false))
    }
  }, [activeTab, currentOrg])

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!currentOrg) return
    setIsSubmittingWs(true)
    try {
      await api.createWorkspace(currentOrg.id, wsName, wsDesc)
      await refreshWorkspaces(currentOrg.id)
      setIsWsModalOpen(false)
      setWsName('')
      setWsDesc('')
    } catch (err: any) {
      alert(`Workspace creation failed: ${err?.detail || 'Error'}`)
    } finally {
      setIsSubmittingWs(false)
    }
  }

  const memberColumns: Column<Membership>[] = [
    {
      header: 'Member Email',
      accessor: (m) => (
        <span className="font-mono text-xs font-semibold text-hc-text">
          {m.user?.email || 'Active User'}
        </span>
      ),
    },
    {
      header: 'Assigned Role',
      accessor: (m) => (
        <Badge
          variant={
            m.role === 'ORG_OWNER'
              ? 'critical'
              : m.role === 'ORG_ADMIN'
              ? 'warning'
              : m.role === 'RELIABILITY_ENGINEER'
              ? 'info'
              : 'neutral'
          }
          size="sm"
        >
          {m.role}
        </Badge>
      ),
    },
    {
      header: 'Joined',
      accessor: (m) => (
        <span className="font-mono text-[11px] text-hc-dim">{formatDateTime(m.created_at)}</span>
      ),
    },
  ]

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-hc-text">Platform Settings</h1>
        <p className="text-xs text-hc-muted mt-1">
          Manage your user profile, organizations, workspaces, and team RBAC permissions
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-hc-border gap-2">
        <button
          onClick={() => setActiveTab('profile')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'profile'
              ? 'border-hc-accent text-white'
              : 'border-transparent text-hc-muted hover:text-hc-text'
          }`}
        >
          <User className="w-3.5 h-3.5" /> User Profile
        </button>

        <button
          onClick={() => setActiveTab('organization')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'organization'
              ? 'border-hc-accent text-white'
              : 'border-transparent text-hc-muted hover:text-hc-text'
          }`}
        >
          <Building className="w-3.5 h-3.5" /> Organization
        </button>

        <button
          onClick={() => setActiveTab('workspaces')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'workspaces'
              ? 'border-hc-accent text-white'
              : 'border-transparent text-hc-muted hover:text-hc-text'
          }`}
        >
          <Layers className="w-3.5 h-3.5" /> Workspaces ({workspaces.length})
        </button>

        <button
          onClick={() => setActiveTab('members')}
          className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'members'
              ? 'border-hc-accent text-white'
              : 'border-transparent text-hc-muted hover:text-hc-text'
          }`}
        >
          <Users className="w-3.5 h-3.5" /> Team Members
        </button>
      </div>

      {/* Tab Content: Profile */}
      {activeTab === 'profile' && (
        <Card className="space-y-4 max-w-xl">
          <h2 className="text-sm font-semibold text-hc-text">Profile Information</h2>
          <div className="space-y-3 text-xs">
            <div>
              <span className="text-hc-dim block">Full Name</span>
              <span className="text-hc-text font-medium text-sm">{user?.full_name || '—'}</span>
            </div>
            <div>
              <span className="text-hc-dim block">Work Email</span>
              <span className="text-hc-text font-mono">{user?.email}</span>
            </div>
            <div>
              <span className="text-hc-dim block">Platform Role</span>
              <Badge variant="info" size="sm" className="mt-1">
                {user?.is_platform_admin ? 'Global Platform Admin' : 'Organization Member'}
              </Badge>
            </div>
          </div>
        </Card>
      )}

      {/* Tab Content: Organization */}
      {activeTab === 'organization' && (
        <Card className="space-y-4 max-w-xl">
          <h2 className="text-sm font-semibold text-hc-text">Active Organization</h2>
          <div className="space-y-3 text-xs">
            <div>
              <span className="text-hc-dim block">Organization Name</span>
              <span className="text-hc-text font-medium text-sm">{currentOrg?.name}</span>
            </div>
            <div>
              <span className="text-hc-dim block">Organization Slug</span>
              <span className="text-hc-text font-mono">{currentOrg?.slug}</span>
            </div>
            <div>
              <span className="text-hc-dim block">Organization ID</span>
              <span className="text-hc-dim font-mono">{currentOrg?.id}</span>
            </div>
            <div>
              <span className="text-hc-dim block">Created At</span>
              <span className="text-hc-text font-mono">{formatDateTime(currentOrg?.created_at)}</span>
            </div>
          </div>
        </Card>
      )}

      {/* Tab Content: Workspaces */}
      {activeTab === 'workspaces' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-sm font-semibold text-hc-text">Tenant Workspaces</h2>
            <Button size="sm" onClick={() => setIsWsModalOpen(true)} icon={<Plus className="w-3.5 h-3.5" />}>
              Add Workspace
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {workspaces.map((ws) => (
              <div
                key={ws.id}
                onClick={() => setCurrentWorkspace(ws)}
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  currentWorkspace?.id === ws.id
                    ? 'border-emerald-400 bg-emerald-950/20'
                    : 'border-hc-border bg-hc-card hover:border-hc-borderHover'
                }`}
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-hc-text">{ws.name}</h3>
                  {currentWorkspace?.id === ws.id && (
                    <Badge variant="healthy" size="sm">
                      Active
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-hc-muted mt-1">{ws.description || 'No description'}</p>
                <span className="text-[10px] font-mono text-hc-dim block mt-3">ID: {ws.id}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab Content: Members */}
      {activeTab === 'members' && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-hc-text">Organization Members</h2>
          <Table columns={memberColumns} data={members} keyExtractor={(m) => m.id} />
        </div>
      )}

      {/* Create Workspace Modal */}
      <Modal
        isOpen={isWsModalOpen}
        onClose={() => setIsWsModalOpen(false)}
        title="Create New Workspace"
        subtitle="Isolate infrastructure environments (e.g. Production, Staging, QA)"
        maxWidth="sm"
      >
        <form onSubmit={handleCreateWorkspace} className="space-y-4">
          <TextInput
            label="Workspace Name"
            value={wsName}
            onChange={(e) => setWsName(e.target.value)}
            placeholder="Staging Environment"
            required
          />

          <TextInput
            label="Description (Optional)"
            value={wsDesc}
            onChange={(e) => setWsDesc(e.target.value)}
            placeholder="Kubernetes cluster in eu-west-1"
          />

          <div className="flex justify-end gap-3 pt-4 border-t border-hc-border">
            <Button type="button" variant="ghost" onClick={() => setIsWsModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmittingWs}>
              Create Workspace
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
