import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import MyPacksPage from './MyPacksPage'

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
  },
}))

import apiClient from '../lib/apiClient'

const mockApiClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
}

function renderPage() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <MyPacksPage />
    </MemoryRouter>,
  )
}

describe('MyPacksPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the list of packs the user belongs to', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        items: [
          {
            id: 1,
            name: 'Moon Pack',
            description: 'Late-night howls and shared dens.',
            image_url: null,
            species_tags: ['Wolf', 'Fox'],
            max_size: 8,
            is_open: true,
            member_count: 3,
            created_at: '2025-01-01T00:00:00Z',
          },
          {
            id: 2,
            name: 'Forest Crew',
            description: null,
            image_url: 'https://example.com/forest.jpg',
            species_tags: null,
            max_size: 5,
            is_open: false,
            member_count: 2,
            created_at: '2025-01-02T00:00:00Z',
          },
        ],
        page: 1,
        limit: 20,
        total: 2,
        has_more: false,
      },
    })

    renderPage()

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/packs/mine')
    })

    expect(await screen.findByRole('list', { name: /my packs/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Moon Pack' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Forest Crew' })).toBeInTheDocument()
    expect(screen.getByText('3 members')).toBeInTheDocument()
    expect(screen.getByText('2 members')).toBeInTheDocument()

    const moonPackLink = screen.getByRole('link', { name: /moon pack/i })
    expect(moonPackLink).toHaveAttribute('href', '/packs/1')
    const forestCrewLink = screen.getByRole('link', { name: /forest crew/i })
    expect(forestCrewLink).toHaveAttribute('href', '/packs/2')
  })

  it('renders an empty state when the user has no packs', async () => {
    mockApiClient.get.mockResolvedValue({
      data: { items: [], page: 1, limit: 20, total: 0, has_more: false },
    })

    renderPage()

    expect(
      await screen.findByText(/you haven't joined any packs yet/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /browse packs/i })).toHaveAttribute('href', '/discover')
    expect(screen.getAllByRole('link', { name: /create pack/i })).toHaveLength(2)
  })

  it('renders an error state when loading fails', async () => {
    mockApiClient.get.mockRejectedValue(new Error('boom'))

    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to load your packs.')
  })

  it('renders a create pack link in the header', async () => {
    mockApiClient.get.mockResolvedValue({
      data: { items: [], page: 1, limit: 20, total: 0, has_more: false },
    })

    renderPage()

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/packs/mine')
    })

    const headerCreateLink = screen.getAllByRole('link', { name: /create pack/i })[0]
    expect(headerCreateLink).toHaveAttribute('href', '/packs/new')
  })
})
