import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import type { User } from './contexts/AuthContext'

vi.mock('./lib/apiClient', () => ({
  default: {
    get: vi.fn((url: string) => {
      if (url === '/species') {
        return Promise.resolve({ data: [] })
      }
      if (url === '/discover') {
        return Promise.resolve({ data: { items: [], page: 1, limit: 20, total: 0, has_more: false } })
      }
      if (url === '/notifications') {
        return Promise.resolve({ data: { items: [], page: 1, limit: 50, total: 0, has_more: false } })
      }
      if (url === '/conversations') {
        return Promise.resolve({ data: [] })
      }
      if (url === '/packs') {
        return Promise.resolve({ data: { items: [], page: 1, limit: 20, total: 0, has_more: false } })
      }
      if (url === '/packs/44') {
        return Promise.resolve({
          data: {
            id: 44,
            creator_id: 2,
            name: 'Moon Pack',
            description: 'Late-night hikes and shared den movie marathons.',
            image_url: null,
            species_tags: ['Wolf', 'Fox'],
            max_size: 6,
            consensus_required: true,
            is_open: true,
            created_at: '2024-01-05T00:00:00Z',
            members: [],
          },
        })
      }
      if (url === '/matches') {
        return Promise.resolve({ data: [] })
      }
      return Promise.reject(new Error(`Unexpected GET ${url}`))
    }),
    post: vi.fn(),
  },
}))

vi.mock('./contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

import { useAuth } from './contexts/AuthContext'

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

function renderWithRouter(initialPath = '/') {
  return render(
    <MemoryRouter
      initialEntries={[initialPath]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <App />
    </MemoryRouter>,
  )
}

describe('App routing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the home page at / when authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    renderWithRouter('/')
    expect(await screen.findByRole('heading', { name: /your den is live/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /quick links/i })).toBeInTheDocument()
  })

  it('redirects to /login at / when not authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: vi.fn() })
    renderWithRouter('/')
    await waitFor(() => {
      expect(screen.getByRole('link', { name: /sign in with google/i })).toBeInTheDocument()
      expect(screen.getByRole('link', { name: /sign in with discord/i })).toBeInTheDocument()
    })
  })

  it('shows loading state at / while auth is loading', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: true, logout: vi.fn() })
    renderWithRouter('/')
    expect(screen.getByText(/loading/i)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /sign in with google/i })).not.toBeInTheDocument()
  })

  it('renders the 404 page for unknown routes', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    renderWithRouter('/this-route-does-not-exist')
    expect(screen.getByRole('heading', { name: /404/i })).toBeInTheDocument()
    expect(screen.getByText(/Page not found/i)).toBeInTheDocument()
  })

  it('does not render the home page content on unknown routes', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    renderWithRouter('/unknown')
    expect(screen.queryByRole('heading', { name: /discover/i })).not.toBeInTheDocument()
  })

  it('renders the login page at /login', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: vi.fn() })
    renderWithRouter('/login')
    expect(screen.getByRole('link', { name: /sign in with google/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign in with discord/i })).toBeInTheDocument()
  })

  it('renders the matches page at /matches when authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    renderWithRouter('/matches')
    expect(await screen.findByRole('heading', { name: /matches/i })).toBeInTheDocument()
    expect(screen.getByText(/you don't have any matches yet/i)).toBeInTheDocument()
  })

  it('renders the notifications page at /notifications when authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    renderWithRouter('/notifications')
    expect(await screen.findByRole('heading', { name: /notifications/i })).toBeInTheDocument()
    expect(screen.getByText(/recent activity across messages, matches, and packs/i)).toBeInTheDocument()
  })

  it('renders the packs discover view at /packs when authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    renderWithRouter('/packs')
    expect(await screen.findByRole('tab', { name: /packs/i })).toHaveAttribute('aria-selected', 'true')
  })

  it('renders the pack detail page at /packs/:packId when authenticated', async () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    renderWithRouter('/packs/44')
    expect(await screen.findAllByRole('heading', { name: 'Moon Pack' })).toHaveLength(2)
    expect(screen.getByText(/late-night hikes and shared den movie marathons/i)).toBeInTheDocument()
  })
})
