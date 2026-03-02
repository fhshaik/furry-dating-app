import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../contexts/AuthContext'
import Header from './Header'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
  },
}))

import { useAuth } from '../contexts/AuthContext'
import apiClient from '../lib/apiClient'

const mockUseAuth = useAuth as ReturnType<typeof vi.fn>
const mockApiClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
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

describe('Header notifications', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it('fetches unread notifications and shows the badge for authenticated users', async () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockResolvedValue({
      data: { items: Array.from({ length: 7 }, () => ({ is_read: false })) },
    })

    render(
      <MemoryRouter initialEntries={['/matches']}>
        <Header />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/notifications', { params: { limit: 100 } })
    })
    expect(screen.getByRole('button', { name: '7 unread notifications' })).toBeInTheDocument()
  })

  it('refreshes the unread badge count on the polling interval', async () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get
      .mockResolvedValueOnce({
        data: { items: [{ is_read: false }] },
      })
      .mockResolvedValueOnce({
        data: { items: Array.from({ length: 3 }, () => ({ is_read: false })) },
      })

    vi.spyOn(window, 'setInterval').mockImplementation((handler) => {
      if (typeof handler === 'function') {
        queueMicrotask(handler)
      }
      return 1 as unknown as ReturnType<typeof setInterval>
    })
    vi.spyOn(window, 'clearInterval').mockImplementation(() => undefined)

    render(
      <MemoryRouter initialEntries={['/matches']}>
        <Header />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(window.setInterval).toHaveBeenCalledWith(expect.any(Function), 30000)
      expect(mockApiClient.get).toHaveBeenCalledTimes(2)
    })
    expect(screen.getByRole('button', { name: '3 unread notifications' })).toBeInTheDocument()
  })

  it('opens the dropdown and navigates to notifications when requested', async () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockResolvedValue({
      data: {
        items: [
          {
            id: 1,
            type: 'message_received',
            payload: { conversation_id: 4 },
            is_read: false,
            created_at: '2026-02-10T15:30:00Z',
          },
          {
            id: 2,
            type: 'match_created',
            payload: { match_id: 8 },
            is_read: false,
            created_at: '2026-02-09T10:00:00Z',
          },
          {
            id: 3,
            type: 'match_created',
            payload: { match_id: 9 },
            is_read: true,
            created_at: '2026-02-08T10:00:00Z',
          },
        ],
      },
    })

    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>,
    )

    const button = await screen.findByRole('button', { name: '2 unread notifications' })
    fireEvent.click(button)
    expect(screen.getByRole('dialog', { name: /recent notifications/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'New message' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /view all/i }))

    expect(mockNavigate).toHaveBeenCalledWith('/notifications')
  })

  it('renders notification rows in the dropdown as links to the relevant destinations', async () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockResolvedValue({
      data: {
        items: [
          {
            id: 1,
            type: 'message_received',
            payload: { conversation_id: 4 },
            is_read: false,
            created_at: '2026-02-10T15:30:00Z',
          },
          {
            id: 2,
            type: 'pack_join_request_received',
            payload: { pack_id: 12 },
            is_read: false,
            created_at: '2026-02-09T10:00:00Z',
          },
        ],
      },
    })

    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>,
    )

    fireEvent.click(await screen.findByRole('button', { name: '2 unread notifications' }))

    expect(screen.getByRole('link', { name: /new message/i })).toHaveAttribute('href', '/inbox/4')
    expect(screen.getByRole('link', { name: /pack join request/i })).toHaveAttribute(
      'href',
      '/packs/12',
    )
  })

  it('does not fetch notifications when the user is logged out', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: vi.fn() })

    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>,
    )

    expect(mockApiClient.get).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: /notifications/i })).not.toBeInTheDocument()
  })
})
