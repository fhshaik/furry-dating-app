import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Header from './Header'
import Nav from './Nav'
import Layout from './Layout'
import type { User } from '../contexts/AuthContext'

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

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApiClient.get.mockResolvedValue({ data: { items: [] } })
  })

  it('renders the app name', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: vi.fn() })
    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>,
    )
    expect(screen.getByText('FurConnect')).toBeInTheDocument()
  })

  it('renders a header element', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: vi.fn() })
    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>,
    )
    expect(screen.getByRole('banner')).toBeInTheDocument()
  })

  it('does not show logout button when user is not logged in', () => {
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: vi.fn() })
    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('button', { name: /logout/i })).not.toBeInTheDocument()
  })

  it('shows logout button when user is logged in', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>,
    )
    expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument()
  })

  it('calls logout and navigates to /login when logout button is clicked', async () => {
    const mockLogout = vi.fn().mockResolvedValue(undefined)
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: mockLogout })

    render(
      <MemoryRouter>
        <Header />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: /logout/i }))

    await waitFor(() => {
      expect(mockLogout).toHaveBeenCalledOnce()
      expect(mockNavigate).toHaveBeenCalledWith('/login')
    })
  })
})

describe('Nav', () => {
  it('renders all nav links', () => {
    render(
      <MemoryRouter>
        <Nav />
      </MemoryRouter>,
    )
    expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /home/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /discover/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /matches/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /packs/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /profile/i })).toBeInTheDocument()
  })

  it('marks the active link', () => {
    render(
      <MemoryRouter initialEntries={['/discover']}>
        <Nav />
      </MemoryRouter>,
    )
    const discoverLink = screen.getByRole('link', { name: /discover/i })
    expect(discoverLink).toHaveAttribute('aria-current', 'page')
    expect(discoverLink.className).toContain('bg-[linear-gradient(135deg,#f2b467,#d87c45)]')
    const homeLink = screen.getByRole('link', { name: /home/i })
    expect(homeLink).not.toHaveAttribute('aria-current')
    expect(homeLink.className).toContain('text-[#f3d9bc]')
  })
})

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({ user: null, loading: false, logout: vi.fn() })
    mockApiClient.get.mockResolvedValue({ data: [] })
  })

  it('renders children inside main', () => {
    render(
      <MemoryRouter>
        <Layout>
          <p>Page content</p>
        </Layout>
      </MemoryRouter>,
    )
    expect(screen.getByRole('main')).toBeInTheDocument()
    expect(screen.getByText('Page content')).toBeInTheDocument()
  })

  it('renders header and nav alongside children', () => {
    render(
      <MemoryRouter>
        <Layout>
          <p>content</p>
        </Layout>
      </MemoryRouter>,
    )
    expect(screen.getByRole('banner')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument()
  })
})
