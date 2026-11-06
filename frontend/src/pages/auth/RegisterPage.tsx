import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Zap, ArrowRight } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/common/Button'
import { TextInput } from '@/components/common/Input'
import { ErrorBanner } from '@/components/common/Feedback'

export const RegisterPage: React.FC = () => {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [organizationName, setOrganizationName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (password.length < 8) {
      setError('Password must be at least 8 characters and include numbers and letters.')
      return
    }

    setIsLoading(true)
    try {
      await register(email, password, fullName, organizationName || undefined)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err?.detail || 'Registration failed. Please check your details.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-hc-bg flex flex-col justify-center items-center p-4">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-tr from-hc-accent to-blue-400 items-center justify-center shadow-xl shadow-hc-accent/25 mb-4">
            <Zap className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-hc-text">Register Organization</h1>
          <p className="text-xs text-hc-muted mt-1.5">
            Set up autonomous self-healing for your cloud infrastructure
          </p>
        </div>

        {/* Card Form */}
        <div className="bg-hc-card border border-hc-border rounded-2xl p-8 shadow-card">
          {error && <ErrorBanner message={error} className="mb-6" />}

          <form onSubmit={handleSubmit} className="space-y-4">
            <TextInput
              label="Full Name"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Sarah Chen"
              required
              autoFocus
            />

            <TextInput
              label="Work Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="sarah@acme-cloud.io"
              required
            />

            <TextInput
              label="Organization Name"
              type="text"
              value={organizationName}
              onChange={(e) => setOrganizationName(e.target.value)}
              placeholder="Acme Cloud Platform"
              helperText="Creates your initial primary tenant organization"
            />

            <TextInput
              label="Password (min. 8 characters, letters & numbers)"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
            />

            <Button
              type="submit"
              className="w-full mt-2"
              size="lg"
              isLoading={isLoading}
              icon={<ArrowRight className="w-4 h-4" />}
            >
              Initialize Workspace
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-hc-border text-center">
            <p className="text-xs text-hc-muted">
              Already have an account?{' '}
              <Link to="/login" className="text-hc-accent hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
