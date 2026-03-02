import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import type { User } from './contexts/AuthContext'

vi.mock('./contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('./lib/apiClient', () => ({
  default: {
    get: vi.fn(),
  },
}))

import { useAuth } from './contexts/AuthContext'
import apiClient from './lib/apiClient'

const mockUseAuth = useAuth as ReturnType<typeof vi.fn>
const mockApiClient = apiClient as unknown as { get: ReturnType<typeof vi.fn> }

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

describe('Tailwind CSS integration', () => {
  it('home page main element keeps the shared layout classes', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockResolvedValue({ data: { items: [], page: 1, limit: 20, total: 0, has_more: false } })
    renderWithRouter('/')
    const main = screen.getByRole('main')
    expect(main.className).toContain('flex-1')
    expect(main.className).toContain('overflow-y-auto')
  })

  it('home page hero heading keeps the redesigned typography classes', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockResolvedValue({ data: { items: [], page: 1, limit: 20, total: 0, has_more: false } })
    renderWithRouter('/')
    const heading = screen.getByRole('heading', { name: /your den is live/i })
    expect(heading.className).toContain('text-4xl')
    expect(heading.className).toContain('font-bold')
  })

  it('home page hero copy keeps the redesigned body text classes', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockResolvedValue({ data: { items: [], page: 1, limit: 20, total: 0, has_more: false } })
    renderWithRouter('/')
    const subtitle = screen.getByText(/built for furs who want warmth, chemistry, and community/i)
    expect(subtitle.className).toContain('text-lg')
    expect(subtitle.className).toContain('leading-8')
  })

  it('404 page main element keeps the shared layout classes', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockResolvedValue({ data: { items: [], page: 1, limit: 20, total: 0, has_more: false } })
    renderWithRouter('/this-route-does-not-exist')
    const main = screen.getByRole('main')
    expect(main.className).toContain('flex-1')
    expect(main.className).toContain('overflow-y-auto')
  })

  it('404 page heading has Tailwind typography classes', () => {
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    renderWithRouter('/this-route-does-not-exist')
    const heading = screen.getByRole('heading', { name: /404/i })
    expect(heading.className).toContain('text-4xl')
    expect(heading.className).toContain('font-bold')
  })
})
