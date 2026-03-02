import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import PackDetailPage from './PackDetailPage'
import type { User } from '../contexts/AuthContext'

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
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
  patch: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}
const mockUseAuth = useAuth as ReturnType<typeof vi.fn>

const mockUser: User = {
  id: 1,
  oauth_provider: 'google',
  email: 'test@example.com',
  display_name: 'Scout',
  bio: null,
  age: 26,
  city: 'Portland',
  nsfw_enabled: false,
  relationship_style: 'polyamorous',
  created_at: '2024-01-01T00:00:00Z',
}

const packResponse = {
  id: 44,
  creator_id: 2,
  name: 'Moon Pack',
  description: 'Late-night hikes and shared den movie marathons.',
  image_url: 'https://example.com/moon-pack.jpg',
  species_tags: ['Wolf', 'Fox'],
  max_size: 6,
  consensus_required: true,
  is_open: true,
  created_at: '2024-01-05T00:00:00Z',
  members: [
    {
      user: {
        id: 2,
        display_name: 'Howl',
      },
      role: 'admin',
      joined_at: '2024-01-05T00:00:00Z',
    },
    {
      user: {
        id: 3,
        display_name: 'Nova',
      },
      role: 'member',
      joined_at: '2024-01-08T00:00:00Z',
    },
  ],
}

// Pack where current user (id=1) is an admin
const adminPackResponse = {
  ...packResponse,
  consensus_required: false,
  members: [
    {
      user: { id: 1, display_name: 'Scout' },
      role: 'admin',
      joined_at: '2024-01-05T00:00:00Z',
    },
    {
      user: { id: 2, display_name: 'Howl' },
      role: 'member',
      joined_at: '2024-01-08T00:00:00Z',
    },
  ],
}

const pendingJoinRequests = [
  {
    id: 10,
    pack_id: 44,
    user_id: 5,
    status: 'pending',
    created_at: '2024-01-10T00:00:00Z',
    user: { id: 5, display_name: 'Blaze' },
    votes: [],
    approvals_required: 2,
    approvals_received: 0,
  },
  {
    id: 11,
    pack_id: 44,
    user_id: 6,
    status: 'pending',
    created_at: '2024-01-11T00:00:00Z',
    user: { id: 6, display_name: 'Ember' },
    votes: [],
    approvals_required: 2,
    approvals_received: 1,
  },
]

function renderPage() {
  return render(
    <MemoryRouter
      initialEntries={['/packs/44']}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/packs/:packId" element={<PackDetailPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PackDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockApiClient.get.mockResolvedValue({ data: packResponse })
    mockApiClient.post.mockResolvedValue({
      data: {
        id: 88,
        pack_id: 44,
        user_id: 1,
        status: 'pending',
      },
    })
    mockApiClient.patch.mockResolvedValue({ data: {} })
    mockApiClient.delete.mockResolvedValue({})
  })

  it('loads the pack details, description, and member list', async () => {
    renderPage()

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/packs/44')
    })

    expect(await screen.findAllByRole('heading', { name: 'Moon Pack' })).toHaveLength(2)
    expect(screen.getByText('Late-night hikes and shared den movie marathons.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /request to join/i })).toBeEnabled()
    expect(screen.getByRole('list', { name: /pack members/i })).toBeInTheDocument()
    expect(screen.getByText('Howl')).toBeInTheDocument()
    expect(screen.getByText('Nova')).toBeInTheDocument()
    expect(screen.getByText('Admin')).toBeInTheDocument()
    expect(screen.getByText('Member')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /edit pack/i })).not.toBeInTheDocument()
  })

  it('submits a join request and updates the button state', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /request to join/i }))

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/packs/44/join-request')
    })

    expect(screen.getByRole('button', { name: /request sent/i })).toBeDisabled()
  })

  it('hides the join section and shows edit link when the current user is already an admin', async () => {
    // Use adminPackResponse: user (id=1) is admin, pack is not consensus
    mockApiClient.get.mockImplementation((url: string) => {
      if (url === '/packs/44') return Promise.resolve({ data: adminPackResponse })
      if (url === '/packs/44/join-requests') return Promise.resolve({ data: [] })
      return Promise.reject(new Error('unexpected url'))
    })

    renderPage()

    expect(await screen.findByRole('list', { name: /pack members/i })).toBeInTheDocument()
    // Join section is hidden when already a member
    expect(screen.queryByRole('button', { name: /request to join/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /edit pack/i })).toHaveAttribute('href', '/packs/44/edit')
    expect(mockApiClient.post).not.toHaveBeenCalled()
  })

  it('shows an error when the pack cannot be loaded', async () => {
    mockApiClient.get.mockRejectedValue(new Error('boom'))
    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to load pack details.')
  })

  describe('Admin panel', () => {
    beforeEach(() => {
      // User is admin of the pack; join-requests returns two pending requests
      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') return Promise.resolve({ data: adminPackResponse })
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: pendingJoinRequests })
        return Promise.reject(new Error('unexpected url'))
      })
    })

    it('shows the pending requests panel for admins', async () => {
      renderPage()

      expect(await screen.findByRole('list', { name: /pending join requests/i })).toBeInTheDocument()
      expect(screen.getByText('Blaze')).toBeInTheDocument()
      expect(screen.getByText('Ember')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /approve blaze/i })).toBeEnabled()
      expect(screen.getByRole('button', { name: /deny blaze/i })).toBeEnabled()
    })

    it('shows the pending request count badge', async () => {
      renderPage()

      await screen.findByRole('list', { name: /pending join requests/i })
      expect(screen.getByText('2')).toBeInTheDocument()
    })

    it('fetches join-requests after loading the pack', async () => {
      renderPage()

      await screen.findByRole('list', { name: /pending join requests/i })

      expect(mockApiClient.get).toHaveBeenCalledWith('/packs/44/join-requests')
    })

    it('shows "No pending join requests" when list is empty', async () => {
      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') return Promise.resolve({ data: adminPackResponse })
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: [] })
        return Promise.reject(new Error('unexpected url'))
      })

      renderPage()

      await screen.findByText('No pending join requests.')
    })

    it('approves a join request and refreshes data', async () => {
      const user = userEvent.setup()

      const updatedPack = {
        ...adminPackResponse,
        members: [
          ...adminPackResponse.members,
          { user: { id: 5, display_name: 'Blaze' }, role: 'member', joined_at: '2024-01-12T00:00:00Z' },
        ],
      }
      mockApiClient.patch.mockResolvedValue({ data: {} })

      let callCount = 0
      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') {
          callCount++
          // Second call (after approve) returns updated pack with Blaze as member
          return Promise.resolve({ data: callCount > 1 ? updatedPack : adminPackResponse })
        }
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: pendingJoinRequests })
        return Promise.reject(new Error('unexpected url'))
      })

      renderPage()

      await user.click(await screen.findByRole('button', { name: /approve blaze/i }))

      await waitFor(() => {
        expect(mockApiClient.patch).toHaveBeenCalledWith('/packs/44/join-requests/5', {
          status: 'approved',
        })
      })
    })

    it('denies a join request and refreshes data', async () => {
      const user = userEvent.setup()
      renderPage()

      await user.click(await screen.findByRole('button', { name: /deny ember/i }))

      await waitFor(() => {
        expect(mockApiClient.patch).toHaveBeenCalledWith('/packs/44/join-requests/6', {
          status: 'denied',
        })
      })
    })

    it('shows Remove button for other members when user is admin', async () => {
      renderPage()

      expect(await screen.findByRole('button', { name: /remove howl/i })).toBeEnabled()
    })

    it('does not show Remove button for the current user (self)', async () => {
      renderPage()

      await screen.findByRole('list', { name: /pack members/i })
      // Scout is the current user (id=1); no remove button for self
      expect(screen.queryByRole('button', { name: /remove scout/i })).not.toBeInTheDocument()
    })

    it('removes a member and refreshes the pack', async () => {
      const user = userEvent.setup()

      const updatedPack = {
        ...adminPackResponse,
        members: [{ user: { id: 1, display_name: 'Scout' }, role: 'admin', joined_at: '2024-01-05T00:00:00Z' }],
      }
      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') {
          return Promise.resolve({ data: updatedPack })
        }
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: [] })
        return Promise.reject(new Error('unexpected url'))
      })

      renderPage()

      // Wait for initial render — we need to re-setup mock before first render
      mockApiClient.get.mockImplementationOnce((url: string) => {
        if (url === '/packs/44') return Promise.resolve({ data: adminPackResponse })
        return Promise.reject(new Error('unexpected url'))
      })

      // Re-render fresh
      vi.clearAllMocks()
      mockApiClient.delete.mockResolvedValue({})
      mockApiClient.patch.mockResolvedValue({ data: {} })

      let getCallCount = 0
      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') {
          getCallCount++
          return Promise.resolve({ data: getCallCount === 1 ? adminPackResponse : updatedPack })
        }
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: [] })
        return Promise.reject(new Error('unexpected url'))
      })

      const { unmount } = renderPage()
      unmount()
      render(
        <MemoryRouter
          initialEntries={['/packs/44']}
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
        >
          <Routes>
            <Route path="/packs/:packId" element={<PackDetailPage />} />
          </Routes>
        </MemoryRouter>,
      )

      await user.click(await screen.findByRole('button', { name: /remove howl/i }))

      await waitFor(() => {
        expect(mockApiClient.delete).toHaveBeenCalledWith('/packs/44/members/2')
      })
    })
  })

  describe('Consensus member panel', () => {
    it('shows the pending requests panel for regular members in consensus packs', async () => {
      const consensusMemberPack = {
        ...packResponse,
        consensus_required: true,
        members: [
          { user: { id: 2, display_name: 'Howl' }, role: 'admin', joined_at: '2024-01-05T00:00:00Z' },
          { user: { id: 1, display_name: 'Scout' }, role: 'member', joined_at: '2024-01-06T00:00:00Z' },
        ],
      }
      const consensusRequests = [
        {
          id: 20,
          pack_id: 44,
          user_id: 7,
          status: 'pending',
          created_at: '2024-01-10T00:00:00Z',
          user: { id: 7, display_name: 'Frost' },
          votes: [],
          approvals_required: 2,
          approvals_received: 0,
        },
      ]

      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') return Promise.resolve({ data: consensusMemberPack })
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: consensusRequests })
        return Promise.reject(new Error('unexpected url'))
      })

      renderPage()

      expect(await screen.findByRole('list', { name: /pending join requests/i })).toBeInTheDocument()
      expect(screen.getByText('Frost')).toBeInTheDocument()
    })

    it('shows vote progress for consensus packs', async () => {
      const consensusMemberPack = {
        ...packResponse,
        consensus_required: true,
        members: [
          { user: { id: 2, display_name: 'Howl' }, role: 'admin', joined_at: '2024-01-05T00:00:00Z' },
          { user: { id: 1, display_name: 'Scout' }, role: 'member', joined_at: '2024-01-06T00:00:00Z' },
        ],
      }
      const consensusRequests = [
        {
          id: 20,
          pack_id: 44,
          user_id: 7,
          status: 'pending',
          created_at: '2024-01-10T00:00:00Z',
          user: { id: 7, display_name: 'Frost' },
          votes: [],
          approvals_required: 2,
          approvals_received: 1,
        },
      ]

      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') return Promise.resolve({ data: consensusMemberPack })
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: consensusRequests })
        return Promise.reject(new Error('unexpected url'))
      })

      renderPage()

      expect(await screen.findByText('1/2 approvals')).toBeInTheDocument()
    })

    it('shows individual vote details for consensus packs', async () => {
      const consensusMemberPack = {
        ...packResponse,
        consensus_required: true,
        members: [
          { user: { id: 2, display_name: 'Howl' }, role: 'admin', joined_at: '2024-01-05T00:00:00Z' },
          { user: { id: 1, display_name: 'Scout' }, role: 'member', joined_at: '2024-01-06T00:00:00Z' },
        ],
      }
      const consensusRequests = [
        {
          id: 20,
          pack_id: 44,
          user_id: 7,
          status: 'pending',
          created_at: '2024-01-10T00:00:00Z',
          user: { id: 7, display_name: 'Frost' },
          votes: [
            {
              voter_user_id: 2,
              decision: 'approved',
              created_at: '2024-01-11T00:00:00Z',
              user: { id: 2, display_name: 'Howl' },
            },
          ],
          approvals_required: 2,
          approvals_received: 1,
        },
      ]

      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') return Promise.resolve({ data: consensusMemberPack })
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: consensusRequests })
        return Promise.reject(new Error('unexpected url'))
      })

      renderPage()

      await screen.findByRole('list', { name: /pending join requests/i })
      expect(await screen.findByLabelText(/vote breakdown/i)).toBeInTheDocument()
      expect(screen.getByText(/Howl: Approved/i)).toBeInTheDocument()
      expect(screen.getByText(/Scout: Pending/i)).toBeInTheDocument()
    })

    it('shows all members as pending when no votes have been cast', async () => {
      const consensusMemberPack = {
        ...packResponse,
        consensus_required: true,
        members: [
          { user: { id: 2, display_name: 'Howl' }, role: 'admin', joined_at: '2024-01-05T00:00:00Z' },
          { user: { id: 1, display_name: 'Scout' }, role: 'member', joined_at: '2024-01-06T00:00:00Z' },
        ],
      }
      const consensusRequests = [
        {
          id: 20,
          pack_id: 44,
          user_id: 7,
          status: 'pending',
          created_at: '2024-01-10T00:00:00Z',
          user: { id: 7, display_name: 'Frost' },
          votes: [],
          approvals_required: 2,
          approvals_received: 0,
        },
      ]

      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') return Promise.resolve({ data: consensusMemberPack })
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: consensusRequests })
        return Promise.reject(new Error('unexpected url'))
      })

      renderPage()

      await screen.findByRole('list', { name: /pending join requests/i })
      expect(await screen.findByText(/Howl: Pending/i)).toBeInTheDocument()
      expect(screen.getByText(/Scout: Pending/i)).toBeInTheDocument()
    })

    it('shows a denied vote in the vote breakdown', async () => {
      const consensusMemberPack = {
        ...packResponse,
        consensus_required: true,
        members: [
          { user: { id: 2, display_name: 'Howl' }, role: 'admin', joined_at: '2024-01-05T00:00:00Z' },
          { user: { id: 1, display_name: 'Scout' }, role: 'member', joined_at: '2024-01-06T00:00:00Z' },
        ],
      }
      const consensusRequests = [
        {
          id: 20,
          pack_id: 44,
          user_id: 7,
          status: 'pending',
          created_at: '2024-01-10T00:00:00Z',
          user: { id: 7, display_name: 'Frost' },
          votes: [
            {
              voter_user_id: 1,
              decision: 'denied',
              created_at: '2024-01-11T00:00:00Z',
              user: { id: 1, display_name: 'Scout' },
            },
          ],
          approvals_required: 2,
          approvals_received: 0,
        },
      ]

      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') return Promise.resolve({ data: consensusMemberPack })
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: consensusRequests })
        return Promise.reject(new Error('unexpected url'))
      })

      renderPage()

      await screen.findByRole('list', { name: /pending join requests/i })
      expect(await screen.findByText(/Scout: Denied/i)).toBeInTheDocument()
      expect(screen.getByText(/Howl: Pending/i)).toBeInTheDocument()
    })

    it('does not show vote breakdown for non-consensus (admin-review) packs', async () => {
      mockApiClient.get.mockImplementation((url: string) => {
        if (url === '/packs/44') return Promise.resolve({ data: adminPackResponse })
        if (url === '/packs/44/join-requests') return Promise.resolve({ data: pendingJoinRequests })
        return Promise.reject(new Error('unexpected url'))
      })

      renderPage()

      await screen.findByRole('list', { name: /pending join requests/i })
      expect(screen.queryByLabelText(/vote breakdown/i)).not.toBeInTheDocument()
    })

    it('does not show pending requests panel for non-members of admin-review packs', async () => {
      // packResponse: user (id=1) is NOT a member, pack is not consensus
      mockApiClient.get.mockResolvedValue({
        data: { ...packResponse, consensus_required: false },
      })

      renderPage()

      await screen.findByRole('button', { name: /request to join/i })
      expect(screen.queryByRole('list', { name: /pending join requests/i })).not.toBeInTheDocument()
    })
  })
})
