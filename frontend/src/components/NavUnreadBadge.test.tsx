import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../contexts/AuthContext'
import Layout from './Layout'
import Nav from './Nav'

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

describe('Nav unread badge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockImplementation((url: string) => {
      if (url === '/conversations') {
        return Promise.resolve({ data: [] })
      }

      if (url === '/notifications') {
        return Promise.resolve({ data: { items: [] } })
      }

      return Promise.reject(new Error(`Unexpected GET ${url}`))
    })
  })

  it('shows unread badge on inbox when count is positive', () => {
    render(
      <MemoryRouter>
        <Nav unreadCount={12} />
      </MemoryRouter>,
    )

    expect(screen.getByLabelText('12 unread messages')).toBeInTheDocument()
  })

  it('fetches conversations and shows the total unread badge for authenticated users', async () => {
    mockApiClient.get.mockImplementation((url: string) => {
      if (url === '/conversations') {
        return Promise.resolve({
          data: [{ unread_count: 2 }, { unread_count: 3 }, { unread_count: 0 }],
        })
      }

      if (url === '/notifications') {
        return Promise.resolve({
          data: { items: [{ is_read: false }, { is_read: false }, { is_read: false }, { is_read: false }] },
        })
      }

      return Promise.reject(new Error(`Unexpected GET ${url}`))
    })

    render(
      <MemoryRouter initialEntries={['/matches']}>
        <Layout>
          <p>content</p>
        </Layout>
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/conversations')
      expect(mockApiClient.get).toHaveBeenCalledWith('/notifications', { params: { limit: 100 } })
    })
    expect(screen.getByLabelText('5 unread messages')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '4 unread notifications' })).toBeInTheDocument()
  })
})
