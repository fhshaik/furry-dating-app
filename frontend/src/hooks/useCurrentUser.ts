import { useAuth } from '../contexts/AuthContext'
import type { User } from '../contexts/AuthContext'

interface UseCurrentUserResult {
  user: User | null
  loading: boolean
}

export function useCurrentUser(): UseCurrentUserResult {
  const { user, loading } = useAuth()
  return { user, loading }
}
