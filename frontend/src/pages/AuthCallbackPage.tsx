import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function AuthCallbackPage() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    if (!loading) {
      if (user) {
        navigate('/', { replace: true })
      } else {
        navigate('/login?error=auth_failed', { replace: true })
      }
    }
  }, [user, loading, navigate])

  return (
    <div className="flex items-center justify-center py-24">
      <p className="text-gray-600">Signing you in…</p>
    </div>
  )
}
