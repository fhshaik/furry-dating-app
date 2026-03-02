import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import MatchesPage from './MatchesPage'

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
      <MatchesPage />
    </MemoryRouter>,
  )
}

describe('MatchesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all 1:1 matches with their last message preview', async () => {
    mockApiClient.get.mockResolvedValue({
      data: [
        {
          id: 11,
          created_at: '2025-02-01T12:00:00Z',
          last_message_preview: 'Want to meet at the con afterparty?',
          matched_user: {
            id: 2,
            display_name: 'River',
            bio: 'Fox artist and coffee enthusiast.',
            age: 29,
            city: 'Portland',
            relationship_style: 'monogamous',
            created_at: '2025-01-01T12:00:00Z',
          },
        },
        {
          id: 12,
          created_at: '2025-02-02T12:00:00Z',
          last_message_preview: null,
          matched_user: {
            id: 3,
            display_name: 'Nova',
            bio: null,
            age: null,
            city: null,
            relationship_style: null,
            created_at: '2025-01-02T12:00:00Z',
          },
        },
      ],
    })

    renderPage()

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/matches')
    })

    expect(await screen.findByRole('heading', { name: 'River, 29' })).toBeInTheDocument()
    expect(screen.getByText('Want to meet at the con afterparty?')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Nova' })).toBeInTheDocument()
    expect(screen.getByText(/no messages yet\. say hello to start the conversation\./i)).toBeInTheDocument()
    expect(screen.getByRole('list', { name: /1:1 matches/i })).toBeInTheDocument()
    expect(screen.getByText('Want to meet at the con afterparty?').closest('li')).toHaveAttribute(
      'id',
      'match-11',
    )
  })

  it('renders an empty state when there are no matches', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })

    renderPage()

    expect(await screen.findByText(/you don't have any matches yet/i)).toBeInTheDocument()
  })

  it('renders an error state when loading fails', async () => {
    mockApiClient.get.mockRejectedValue(new Error('boom'))

    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(/failed to load matches/i)
  })
})
