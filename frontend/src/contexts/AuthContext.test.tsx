import { render, screen, waitFor, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthProvider, useAuth } from './AuthContext'
import type { User } from './AuthContext'

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import apiClient from '../lib/apiClient'

const mockApiClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
}

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

function TestConsumer() {
  const { user, loading, logout } = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(loading)}</span>
      <span data-testid="user">{user ? user.display_name : 'null'}</span>
      <button onClick={logout}>Logout</button>
    </div>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('starts with loading=true and user=null', async () => {
    // Delay the resolution so we can observe the initial state
    let resolve: (value: unknown) => void
    mockApiClient.get.mockReturnValue(new Promise((res) => { resolve = res }))

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    expect(screen.getByTestId('loading').textContent).toBe('true')
    expect(screen.getByTestId('user').textContent).toBe('null')

    // Resolve to avoid unhandled promise
    await act(async () => { resolve!({ data: mockUser }) })
  })

  it('sets user and loading=false after successful fetch', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockUser })

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false')
    })
    expect(screen.getByTestId('user').textContent).toBe('Test User')
  })

  it('sets user=null and loading=false when fetch fails (unauthenticated)', async () => {
    mockApiClient.get.mockRejectedValue(new Error('401'))

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('loading').textContent).toBe('false')
    })
    expect(screen.getByTestId('user').textContent).toBe('null')
  })

  it('calls /auth/logout and clears user on logout', async () => {
    mockApiClient.get.mockResolvedValue({ data: mockUser })
    mockApiClient.post.mockResolvedValue({})

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('user').textContent).toBe('Test User')
    })

    await act(async () => {
      screen.getByRole('button', { name: /logout/i }).click()
    })

    expect(mockApiClient.post).toHaveBeenCalledWith('/auth/logout')
    expect(screen.getByTestId('user').textContent).toBe('null')
  })
})

describe('useAuth', () => {
  it('throws when used outside AuthProvider', () => {
    // Suppress the error output React logs for thrown errors during render
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    function BadConsumer() {
      useAuth()
      return null
    }

    expect(() => render(<BadConsumer />)).toThrow('useAuth must be used within AuthProvider')

    consoleError.mockRestore()
  })
})
