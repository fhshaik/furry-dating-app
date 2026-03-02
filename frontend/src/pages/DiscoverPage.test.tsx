import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import DiscoverPage from './DiscoverPage'
import type { User } from '../contexts/AuthContext'

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

import apiClient from '../lib/apiClient'
import { useAuth } from '../contexts/AuthContext'

const mockApiClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
}
const mockUseAuth = useAuth as ReturnType<typeof vi.fn>

const mockUser: User = {
  id: 1,
  oauth_provider: 'google',
  email: 'test@example.com',
  display_name: 'Test User',
  bio: null,
  age: 25,
  city: 'Portland',
  nsfw_enabled: true,
  relationship_style: 'polyamorous',
  created_at: '2024-01-01T00:00:00Z',
}

const speciesResponse = [
  { id: 1, name: 'Fox', slug: 'fox' },
  { id: 2, name: 'Wolf', slug: 'wolf' },
]

const discoverResponse = {
  items: [
    {
      id: 2,
      display_name: 'River',
      bio: 'Coffee and conventions.',
      age: 29,
      city: 'Portland',
      relationship_style: 'monogamous',
      created_at: '2024-01-02T00:00:00Z',
      fursona: {
        name: 'Cinder',
        species: 'Fox',
        traits: ['playful', 'creative'],
        image_url: 'https://example.com/cinder.jpg',
      },
    },
    {
      id: 3,
      display_name: 'Nova',
      bio: 'Night hikes and synth playlists.',
      age: 27,
      city: 'Seattle',
      relationship_style: 'open',
      created_at: '2024-01-03T00:00:00Z',
      fursona: {
        name: 'Nova',
        species: 'Wolf',
        traits: ['adventurous'],
        image_url: null,
      },
    },
  ],
  page: 1,
  limit: 20,
  total: 2,
  has_more: false,
}

const packDiscoverResponse = {
  items: [
    {
      id: 44,
      name: 'Moon Pack',
      description: 'Late-night hikes and shared den movie marathons.',
      image_url: 'https://example.com/moon-pack.jpg',
      species_tags: ['Wolf', 'Fox'],
      max_size: 6,
      member_count: 3,
      is_open: true,
      consensus_required: true,
      created_at: '2024-01-05T00:00:00Z',
    },
  ],
  page: 1,
  limit: 20,
  total: 1,
  has_more: false,
}

function renderPage() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <DiscoverPage />
    </MemoryRouter>,
  )
}

describe('DiscoverPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockImplementation((url: string) => {
      if (url === '/species') {
        return Promise.resolve({ data: speciesResponse })
      }
      if (url === '/discover') {
        return Promise.resolve({ data: discoverResponse })
      }
      if (url === '/packs') {
        return Promise.resolve({ data: packDiscoverResponse })
      }
      return Promise.reject(new Error(`Unexpected GET ${url}`))
    })
    mockApiClient.post.mockResolvedValue({
      data: {
        id: 101,
        swiper_id: 1,
        target_user_id: 2,
        target_pack_id: null,
        action: 'like',
        created_at: '2024-01-04T00:00:00Z',
        is_match: false,
      },
    })
  })

  it('loads species options and initial discover results', async () => {
    renderPage()

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/species')
      expect(mockApiClient.get).toHaveBeenCalledWith('/discover', {
        params: {
          species: undefined,
          city: undefined,
          min_age: undefined,
          max_age: undefined,
          relationship_style: undefined,
          include_nsfw: true,
        },
      })
    })

    expect(screen.getByRole('button', { name: /filters/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Cinder' })).toBeInTheDocument()
    expect(screen.getAllByText('Fox').length).toBeGreaterThan(0)
    expect(screen.getByText(/Playful/)).toBeInTheDocument()
    expect(screen.getByLabelText(/swipe card stack/i)).toBeInTheDocument()
  })

  it('links the active pack card to the detail page from the packs tab', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('tab', { name: /packs/i }))

    expect(await screen.findByRole('heading', { name: 'Moon Pack' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /view pack details/i })).toHaveAttribute('href', '/packs/44')
  })

  it('shows a create pack entry point from the packs tab', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('tab', { name: /packs/i }))

    expect(screen.getByRole('link', { name: /create pack/i })).toHaveAttribute('href', '/packs/new')
  })

  it('submits selected filters from the drawer as discover query params', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Cinder' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /filters/i }))

    expect(screen.getByRole('dialog', { name: /filter drawer/i })).toBeInTheDocument()
    await user.click(screen.getByRole('checkbox', { name: 'Fox' }))
    await user.click(screen.getByRole('checkbox', { name: 'Wolf' }))
    await user.type(screen.getByLabelText(/^city$/i), 'Port')
    await user.selectOptions(screen.getByLabelText(/relationship style/i), 'monogamous')
    fireEvent.change(screen.getByLabelText(/minimum age/i), { target: { value: '26' } })
    fireEvent.change(screen.getByLabelText(/maximum age/i), { target: { value: '32' } })
    await user.click(screen.getByRole('button', { name: /apply filters/i }))

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenLastCalledWith('/discover', {
        params: {
          species: 'Fox,Wolf',
          city: 'Port',
          min_age: 26,
          max_age: 32,
          relationship_style: 'monogamous',
          include_nsfw: true,
        },
      })
    })
  })

  it('keeps NSFW filter disabled when the current user has NSFW disabled', async () => {
    const user = userEvent.setup()
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, nsfw_enabled: false },
      loading: false,
      logout: vi.fn(),
    })

    renderPage()

    await user.click(screen.getByRole('button', { name: /filters/i }))
    const checkbox = screen.getByLabelText(/include nsfw profiles/i)
    expect(checkbox).toBeDisabled()

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/discover', {
        params: {
          species: undefined,
          city: undefined,
          min_age: undefined,
          max_age: undefined,
          relationship_style: undefined,
          include_nsfw: false,
        },
      })
    })
  })

  it('resets drawer filters back to defaults', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Cinder' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /filters/i }))
    await user.click(screen.getByRole('checkbox', { name: 'Fox' }))
    await user.type(screen.getByLabelText(/^city$/i), 'Port')
    fireEvent.change(screen.getByLabelText(/minimum age/i), { target: { value: '26' } })
    fireEvent.change(screen.getByLabelText(/maximum age/i), { target: { value: '32' } })
    await user.click(screen.getByRole('button', { name: /^reset$/i }))

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenLastCalledWith('/discover', {
        params: {
          species: undefined,
          city: undefined,
          min_age: undefined,
          max_age: undefined,
          relationship_style: undefined,
          include_nsfw: true,
        },
      })
    })

    expect(screen.queryByRole('dialog', { name: /filter drawer/i })).not.toBeInTheDocument()
  })

  it('posts a like swipe and advances the deck', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Cinder' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^like$/i }))

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/swipes', {
        action: 'like',
        target_user_id: 2,
      })
    })

    const topCard = screen.getByRole('heading', { name: 'Cinder' }).closest('article')
    expect(topCard).not.toBeNull()
    expect(topCard as HTMLElement).toHaveStyle({
      opacity: '0',
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Nova' })).toBeInTheDocument()
    })
    expect(screen.queryByRole('heading', { name: 'Cinder' })).not.toBeInTheDocument()
  })

  it('posts a pass swipe from the pass button and advances the deck', async () => {
    mockApiClient.post.mockResolvedValueOnce({
      data: {
        id: 103,
        swiper_id: 1,
        target_user_id: 2,
        target_pack_id: null,
        action: 'pass',
        created_at: '2024-01-04T00:00:00Z',
        is_match: false,
      },
    })

    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Cinder' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^pass$/i }))

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/swipes', {
        action: 'pass',
        target_user_id: 2,
      })
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Nova' })).toBeInTheDocument()
    })
  })

  it('posts a like swipe when the user swipes right on the top card', async () => {
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Cinder' })).toBeInTheDocument()

    const card = screen.getByRole('heading', { name: 'Cinder' }).closest('article')
    expect(card).not.toBeNull()

    fireEvent.touchStart(card as HTMLElement, {
      touches: [{ clientX: 20, clientY: 10 }],
    })
    fireEvent.touchMove(card as HTMLElement, {
      touches: [{ clientX: 180, clientY: 10 }],
    })
    fireEvent.touchEnd(card as HTMLElement)

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/swipes', {
        action: 'like',
        target_user_id: 2,
      })
    })
  })

  it('posts a pass swipe when the user swipes left on the top card', async () => {
    mockApiClient.post.mockResolvedValueOnce({
      data: {
        id: 104,
        swiper_id: 1,
        target_user_id: 2,
        target_pack_id: null,
        action: 'pass',
        created_at: '2024-01-04T00:00:00Z',
        is_match: false,
      },
    })

    renderPage()

    expect(await screen.findByRole('heading', { name: 'Cinder' })).toBeInTheDocument()

    const card = screen.getByRole('heading', { name: 'Cinder' }).closest('article')
    expect(card).not.toBeNull()

    fireEvent.touchStart(card as HTMLElement, {
      touches: [{ clientX: 200, clientY: 10 }],
    })
    fireEvent.touchMove(card as HTMLElement, {
      touches: [{ clientX: 40, clientY: 10 }],
    })
    fireEvent.touchEnd(card as HTMLElement)

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/swipes', {
        action: 'pass',
        target_user_id: 2,
      })
    })
  })

  it('shows a match overlay after a successful mutual like', async () => {
    mockApiClient.post.mockResolvedValueOnce({
      data: {
        id: 102,
        swiper_id: 1,
        target_user_id: 2,
        target_pack_id: null,
        action: 'like',
        created_at: '2024-01-04T00:00:00Z',
        is_match: true,
      },
    })

    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Cinder' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^like$/i }))

    expect(await screen.findByRole('heading', { name: "It's a Match!" })).toBeInTheDocument()
    expect(screen.getByText(/you and river liked each other/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /keep swiping/i })).toBeInTheDocument()
  })

  it('loads pack cards from the packs tab and applies pack filters', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Cinder' })).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Packs' }))

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/packs', {
        params: {
          species: undefined,
          search: undefined,
        },
      })
    })

    expect(await screen.findByRole('heading', { name: 'Moon Pack' })).toBeInTheDocument()
    expect(screen.getByText(/browse open packs/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /filters/i }))
    await user.click(screen.getByRole('checkbox', { name: 'Fox' }))
    await user.type(screen.getByLabelText(/^search$/i), 'moon')
    await user.click(screen.getByRole('button', { name: /apply filters/i }))

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenLastCalledWith('/packs', {
        params: {
          species: 'Fox',
          search: 'moon',
        },
      })
    })
  })

  it('posts a pack like swipe using target_pack_id from the packs tab', async () => {
    mockApiClient.post.mockResolvedValueOnce({
      data: {
        id: 106,
        swiper_id: 1,
        target_user_id: null,
        target_pack_id: 44,
        action: 'like',
        created_at: '2024-01-06T00:00:00Z',
        is_match: false,
      },
    })

    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('tab', { name: 'Packs' }))
    expect(await screen.findByRole('heading', { name: 'Moon Pack' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^like$/i }))

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/swipes', {
        action: 'like',
        target_pack_id: 44,
      })
    })
  })

  it('posts a pack pass swipe when the user swipes left on the top card in the packs tab', async () => {
    mockApiClient.post.mockResolvedValueOnce({
      data: {
        id: 107,
        swiper_id: 1,
        target_user_id: null,
        target_pack_id: 44,
        action: 'pass',
        created_at: '2024-01-06T00:00:00Z',
        is_match: false,
      },
    })

    renderPage()

    await userEvent.setup().click(await screen.findByRole('tab', { name: 'Packs' }))
    expect(await screen.findByRole('heading', { name: 'Moon Pack' })).toBeInTheDocument()

    const card = screen.getByRole('heading', { name: 'Moon Pack' }).closest('article')
    expect(card).not.toBeNull()

    fireEvent.touchStart(card as HTMLElement, {
      touches: [{ clientX: 200, clientY: 10 }],
    })
    fireEvent.touchMove(card as HTMLElement, {
      touches: [{ clientX: 40, clientY: 10 }],
    })
    fireEvent.touchEnd(card as HTMLElement)

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/swipes', {
        action: 'pass',
        target_pack_id: 44,
      })
    })
  })

  it('dismisses the match overlay when keep swiping is pressed', async () => {
    mockApiClient.post.mockResolvedValueOnce({
      data: {
        id: 105,
        swiper_id: 1,
        target_user_id: 2,
        target_pack_id: null,
        action: 'like',
        created_at: '2024-01-04T00:00:00Z',
        is_match: true,
      },
    })

    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Cinder' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /^like$/i }))

    const dismissButton = await screen.findByRole('button', { name: /keep swiping/i })
    await user.click(dismissButton)

    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: "It's a Match!" })).not.toBeInTheDocument()
    })
  })
})
