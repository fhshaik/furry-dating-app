import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useCurrentUser } from './useCurrentUser'
import type { User } from '../contexts/AuthContext'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from '../contexts/AuthContext'
const mockUseAuth = useAuth as ReturnType<typeof vi.fn>

const mockUser: User = {
  id: 1,
  oauth_provider: 'google',
  email: 'test@example.com',
  display_name: 'Test User',
  bio: null,
  age: 25,
  city: null,
  nsfw_enabled: false,
  relationship_style: null,
  created_at: '2024-01-01T00:00:00Z',
}

describe('useCurrentUser', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns user and loading from auth context', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })

    const { result } = renderHook(() => useCurrentUser())

    expect(result.current.user).toEqual(mockUser)
    expect(result.current.loading).toBe(false)
  })

  it('returns null user and loading=true when auth is loading', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true, logout: vi.fn() })

    const { result } = renderHook(() => useCurrentUser())

    expect(result.current.user).toBeNull()
    expect(result.current.loading).toBe(true)
  })

  it('returns null user and loading=false when unauthenticated', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: vi.fn() })

    const { result } = renderHook(() => useCurrentUser())

    expect(result.current.user).toBeNull()
    expect(result.current.loading).toBe(false)
  })

  it('does not expose logout from auth context', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })

    const { result } = renderHook(() => useCurrentUser())

    expect(result.current).not.toHaveProperty('logout')
  })
})
