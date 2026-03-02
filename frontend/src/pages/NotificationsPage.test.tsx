import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import NotificationsPage from './NotificationsPage'

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    patch: vi.fn(),
  },
}))

import apiClient from '../lib/apiClient'

const mockApiClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
  patch: ReturnType<typeof vi.fn>
}

function renderPage() {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <NotificationsPage />
    </MemoryRouter>,
  )
}

describe('NotificationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders recent notifications from the API', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        items: [
          {
            id: 1,
            type: 'message_received',
            payload: { conversation_id: 12 },
            is_read: false,
            created_at: '2026-02-10T15:30:00Z',
          },
          {
            id: 2,
            type: 'match_created',
            payload: { match_id: 7 },
            is_read: true,
            created_at: '2026-02-09T10:00:00Z',
          },
          {
            id: 3,
            type: 'pack_join_request_received',
            payload: { pack_id: 21 },
            is_read: true,
            created_at: '2026-02-08T10:00:00Z',
          },
        ],
      },
    })

    renderPage()

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/notifications', { params: { limit: 50 } })
    })

    expect(await screen.findByRole('heading', { name: 'New message' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'New match' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Pack join request' })).toBeInTheDocument()
    expect(screen.getAllByLabelText('Unread notification')).toHaveLength(1)
    expect(screen.getByRole('link', { name: /new message/i })).toHaveAttribute('href', '/inbox/12')
    expect(screen.getByRole('link', { name: /new match/i })).toHaveAttribute('href', '/matches#match-7')
    expect(screen.getByRole('link', { name: /pack join request/i })).toHaveAttribute(
      'href',
      '/packs/21',
    )
  })

  it('marks all notifications as read', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        items: [
          {
            id: 1,
            type: 'message_received',
            payload: null,
            is_read: false,
            created_at: '2026-02-10T15:30:00Z',
          },
        ],
      },
    })
    mockApiClient.patch.mockResolvedValue({ status: 204 })

    renderPage()

    const button = await screen.findByRole('button', { name: /mark all as read/i })
    fireEvent.click(button)

    await waitFor(() => {
      expect(mockApiClient.patch).toHaveBeenCalledWith('/notifications/read-all')
    })

    expect(screen.queryByLabelText('Unread notification')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /mark all as read/i })).toBeDisabled()
  })

  it('renders empty state when there are no notifications', async () => {
    mockApiClient.get.mockResolvedValue({
      data: {
        items: [],
      },
    })

    renderPage()

    expect(await screen.findByText(/no notifications yet/i)).toBeInTheDocument()
    expect(screen.getByText(/new activity will show up here/i)).toBeInTheDocument()
  })

  it('renders an error state when loading fails', async () => {
    mockApiClient.get.mockRejectedValue(new Error('boom'))

    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(/failed to load notifications/i)
  })
})
