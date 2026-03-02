import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import InboxPage from './InboxPage'

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
      <InboxPage />
    </MemoryRouter>,
  )
}

describe('InboxPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders direct and pack conversations', async () => {
    mockApiClient.get.mockResolvedValue({
      data: [
        {
          id: 1,
          type: 'direct',
          pack_id: null,
          created_at: '2026-01-15T10:00:00Z',
          unread_count: 2,
        },
        {
          id: 2,
          type: 'pack',
          pack_id: 7,
          created_at: '2026-01-20T12:00:00Z',
          unread_count: 0,
        },
      ],
    })

    renderPage()

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/conversations')
    })

    expect(await screen.findByRole('heading', { name: 'Direct Message' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Pack Chat #7' })).toBeInTheDocument()
    expect(screen.getByText('Direct')).toBeInTheDocument()
    expect(screen.getByText('Pack')).toBeInTheDocument()
    expect(screen.getByText('2 unread')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: /conversations/i })).toBeInTheDocument()
  })

  it('renders empty state when there are no conversations', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })

    renderPage()

    expect(await screen.findByText(/no conversations yet/i)).toBeInTheDocument()
    expect(screen.getByText(/match with someone or join a pack/i)).toBeInTheDocument()
  })

  it('renders an error state when loading fails', async () => {
    mockApiClient.get.mockRejectedValue(new Error('network error'))

    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(/failed to load conversations/i)
  })

  it('renders loading state initially', () => {
    mockApiClient.get.mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByText(/loading conversations/i)).toBeInTheDocument()
  })

  it('renders the page heading', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })

    renderPage()

    expect(screen.getByRole('heading', { name: 'Inbox' })).toBeInTheDocument()
    expect(screen.getByText(/all your direct and pack conversations/i)).toBeInTheDocument()
  })
})
