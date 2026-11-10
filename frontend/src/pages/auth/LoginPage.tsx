import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Zap, Lock, Mail, ArrowRight } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { Button } from '@/components/common/Button'
import { TextInput } from '@/components/common/Input'
import { ErrorBanner } from '@/components/common/Feedback'

export const LoginPage: React.FC = () => {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err: any) {
      setError(err?.detail || 'Authentication failed. Please verify your credentials.')
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
          <h1 className="text-2xl font-bold tracking-tight text-hc-text">Sign in to HealCloud</h1>
          <p className="text-xs text-hc-muted mt-1.5">
            Autonomous Cloud Reliability & Self-Healing Platform
          </p>
        </div>

        {/* Card Form */}
        <div className="bg-hc-card border border-hc-border rounded-2xl p-8 shadow-card">
          {error && <ErrorBanner message={error} className="mb-6" />}

          <form onSubmit={handleSubmit} className="space-y-4">
            <TextInput
              label="Email Address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="sre@acme-cloud.io"
              required
              autoFocus
            />

            <TextInput
              label="Password"
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
              Sign In to Console
            </Button>
          </form>

          <div className="mt-6 pt-6 border-t border-hc-border text-center">
            <p className="text-xs text-hc-muted">
              Don't have a team account?{' '}
              <Link to="/register" className="text-hc-accent hover:underline font-medium">
                Create an organization
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

