import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { User, Organization, Workspace } from '@/types'
import { api } from '@/api/client'

interface AuthContextType {
  user: User | null
  token: string | null
  organizations: Organization[]
  currentOrg: Organization | null
  workspaces: Workspace[]
  currentWorkspace: Workspace | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string, orgName?: string) => Promise<void>
  logout: () => Promise<void>
  setCurrentOrg: (org: Organization) => void
  setCurrentWorkspace: (ws: Workspace) => void
  refreshWorkspaces: (orgId: string) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('hc_token'))
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [currentOrg, setCurrentOrgState] = useState<Organization | null>(null)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [currentWorkspace, setCurrentWorkspaceState] = useState<Workspace | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  // Listen to 401 events from ApiClient
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null)
      setToken(null)
      setCurrentOrgState(null)
      setCurrentWorkspaceState(null)
    }
    window.addEventListener('hc_unauthorized', handleUnauthorized)
    return () => window.removeEventListener('hc_unauthorized', handleUnauthorized)
  }, [])

  // Initial session restoration
  useEffect(() => {
    const restoreSession = async () => {
      const storedToken = localStorage.getItem('hc_token')
      if (!storedToken) {
        setIsLoading(false)
        return
      }

      try {
        const { user } = await api.getProfile()
        setUser(user)

        const orgs = await api.listOrganizations()
        setOrganizations(orgs)

        if (orgs.length > 0) {
          const savedOrgId = localStorage.getItem('hc_org_id')
          const selectedOrg = orgs.find((o) => o.id === savedOrgId) || orgs[0]
          setCurrentOrgState(selectedOrg)
          localStorage.setItem('hc_org_id', selectedOrg.id)

          const wsList = await api.listWorkspaces(selectedOrg.id)
          setWorkspaces(wsList)

          if (wsList.length > 0) {
            const savedWsId = localStorage.getItem('hc_ws_id')
            const selectedWs = wsList.find((w) => w.id === savedWsId) || wsList[0]
            setCurrentWorkspaceState(selectedWs)
            localStorage.setItem('hc_ws_id', selectedWs.id)
          }
        }
      } catch (err) {
        console.warn('Failed to restore user session:', err)
        api.clearToken()
        setToken(null)
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }

    restoreSession()
  }, [])

  const refreshWorkspaces = async (orgId: string) => {
    try {
      const wsList = await api.listWorkspaces(orgId)
      setWorkspaces(wsList)
      if (wsList.length > 0 && (!currentWorkspace || currentWorkspace.organization_id !== orgId)) {
        setCurrentWorkspaceState(wsList[0])
        localStorage.setItem('hc_ws_id', wsList[0].id)
      }
    } catch (e) {
      console.error('Failed to refresh workspaces:', e)
    }
  }

  const setCurrentOrg = (org: Organization) => {
    setCurrentOrgState(org)
    localStorage.setItem('hc_org_id', org.id)
    refreshWorkspaces(org.id)
  }

  const setCurrentWorkspace = (ws: Workspace) => {
    setCurrentWorkspaceState(ws)
    localStorage.setItem('hc_ws_id', ws.id)
  }

  const login = async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const res = await api.login(email, password)
      setToken(res.access_token)
      setUser(res.user)

      const orgs = await api.listOrganizations()
      setOrganizations(orgs)

      if (orgs.length > 0) {
        const org = orgs[0]
        setCurrentOrgState(org)
        localStorage.setItem('hc_org_id', org.id)

        const wsList = await api.listWorkspaces(org.id)
        setWorkspaces(wsList)
        if (wsList.length > 0) {
          setCurrentWorkspaceState(wsList[0])
          localStorage.setItem('hc_ws_id', wsList[0].id)
        }
      }
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (email: string, password: string, fullName: string, orgName?: string) => {
    setIsLoading(true)
    try {
      const res = await api.register({
        email,
        password,
        full_name: fullName,
        organization_name: orgName,
      })
      setToken(res.access_token)
      setUser(res.user)

      const orgs = await api.listOrganizations()
      setOrganizations(orgs)

      if (orgs.length > 0) {
        const org = orgs[0]
        setCurrentOrgState(org)
        localStorage.setItem('hc_org_id', org.id)

        const wsList = await api.listWorkspaces(org.id)
        setWorkspaces(wsList)
        if (wsList.length > 0) {
          setCurrentWorkspaceState(wsList[0])
          localStorage.setItem('hc_ws_id', wsList[0].id)
        }
      }
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async () => {
    try {
      await api.logout()
    } finally {
      setUser(null)
      setToken(null)
      setOrganizations([])
      setWorkspaces([])
      setCurrentOrgState(null)
      setCurrentWorkspaceState(null)
      localStorage.removeItem('hc_org_id')
      localStorage.removeItem('hc_ws_id')
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        organizations,
        currentOrg,
        workspaces,
        currentWorkspace,
        isLoading,
        login,
        register,
        logout,
        setCurrentOrg,
        setCurrentWorkspace,
        refreshWorkspaces,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

