import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ConversationViewPage from './ConversationViewPage'
import type { User } from '../contexts/AuthContext'

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
  },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

import apiClient from '../lib/apiClient'
import { useAuth } from '../contexts/AuthContext'

const mockApiClient = apiClient as unknown as { get: ReturnType<typeof vi.fn> }
const mockUseAuth = useAuth as ReturnType<typeof vi.fn>

const mockUser: User = {
  id: 42,
  oauth_provider: 'discord',
  email: 'fox@example.com',
  display_name: 'Foxy',
  bio: null,
  age: 24,
  city: 'Austin',
  nsfw_enabled: false,
  relationship_style: null,
  created_at: '2024-01-01T00:00:00Z',
}

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  static CONNECTING = 0
  static CLOSING = 2
  static CLOSED = 3

  onopen: ((e: Event) => void) | null = null
  onclose: ((e: CloseEvent) => void) | null = null
  onerror: ((e: Event) => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  readyState = 1 // OPEN

  send = vi.fn()
  close = vi.fn()

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
    // Simulate connection open on next tick
    setTimeout(() => {
      this.onopen?.(new Event('open'))
    }, 0)
  }

  simulateMessage(data: object) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }
}

function renderPage(conversationId = '5') {
  return render(
    <MemoryRouter
      initialEntries={[`/inbox/${conversationId}`]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <Routes>
        <Route path="/inbox/:conversationId" element={<ConversationViewPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ConversationViewPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    // jsdom does not implement scrollIntoView
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders loading state initially', () => {
    mockApiClient.get.mockReturnValue(new Promise(() => {}))

    renderPage()

    expect(screen.getByText(/loading messages/i)).toBeInTheDocument()
  })

  it('renders messages in chronological order after loading', async () => {
    mockApiClient.get.mockResolvedValue({
      data: [
        // API returns newest-first; component reverses for display
        {
          id: 2,
          conversation_id: 5,
          sender_id: 99,
          content: 'Hi there!',
          sent_at: '2026-01-15T10:01:00Z',
          is_read: false,
        },
        {
          id: 1,
          conversation_id: 5,
          sender_id: 42,
          content: 'Hello!',
          sent_at: '2026-01-15T10:00:00Z',
          is_read: true,
        },
      ],
    })

    renderPage()

    expect(await screen.findByText('Hello!')).toBeInTheDocument()
    expect(screen.getByText('Hi there!')).toBeInTheDocument()
    expect(screen.getByRole('log', { name: /messages/i })).toBeInTheDocument()
  })

  it('shows empty state when there are no messages', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })

    renderPage()

    expect(await screen.findByText(/no messages yet/i)).toBeInTheDocument()
  })

  it('shows error state when loading fails', async () => {
    mockApiClient.get.mockRejectedValue(new Error('network error'))

    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(/failed to load messages/i)
  })

  it('renders a back to inbox link', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })

    renderPage()

    await screen.findByText(/no messages yet/i)
    expect(screen.getByRole('link', { name: /back to inbox/i })).toBeInTheDocument()
  })

  it('renders the page heading', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })

    renderPage()

    await screen.findByText(/no messages yet/i)
    expect(screen.getByRole('heading', { name: /conversation/i })).toBeInTheDocument()
  })

  it('sends a message when Send button is clicked', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })
    const user = userEvent.setup()

    renderPage()

    await screen.findByText(/no messages yet/i)
    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))

    const input = screen.getByRole('textbox', { name: /message input/i })
    // Type first, then wait for button to be enabled (needs non-empty input + wsReady)
    await user.type(input, 'Hey pack!')
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /send message/i })).not.toBeDisabled(),
    )
    await user.click(screen.getByRole('button', { name: /send message/i }))

    expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
      JSON.stringify({ content: 'Hey pack!' }),
    )
    // Input should be cleared after send
    expect(input).toHaveValue('')
  })

  it('sends a message when Enter is pressed', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })
    const user = userEvent.setup()

    renderPage()

    await screen.findByText(/no messages yet/i)
    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))

    const input = screen.getByRole('textbox', { name: /message input/i })
    await user.type(input, 'Hello{Enter}')

    // The keydown handler calls sendMessage which checks ws.readyState === WebSocket.OPEN
    // MockWebSocket.readyState is 1 (OPEN) from construction, so send should be called
    await waitFor(() => {
      expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
        JSON.stringify({ content: 'Hello' }),
      )
    })
  })

  it('does not send an empty message', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })
    const user = userEvent.setup()

    renderPage()

    await screen.findByText(/no messages yet/i)
    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))

    const sendBtn = screen.getByRole('button', { name: /send message/i })
    // Button should be disabled with empty input
    expect(sendBtn).toBeDisabled()

    await user.click(sendBtn)
    expect(MockWebSocket.instances[0].send).not.toHaveBeenCalled()
  })

  it('appends an incoming WebSocket message', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })

    renderPage()

    await screen.findByText(/no messages yet/i)
    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'message',
        id: 10,
        conversation_id: 5,
        sender_id: 99,
        content: 'Incoming message!',
        sent_at: '2026-01-15T10:05:00Z',
        is_read: false,
      })
    })

    expect(await screen.findByText('Incoming message!')).toBeInTheDocument()
  })

  it('does not duplicate a message already in state', async () => {
    mockApiClient.get.mockResolvedValue({
      data: [
        {
          id: 5,
          conversation_id: 5,
          sender_id: 42,
          content: 'Already here',
          sent_at: '2026-01-15T10:00:00Z',
          is_read: true,
        },
      ],
    })

    renderPage()

    await screen.findByText('Already here')
    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'message',
        id: 5,
        conversation_id: 5,
        sender_id: 42,
        content: 'Already here',
        sent_at: '2026-01-15T10:00:00Z',
        is_read: true,
      })
    })

    // Should still have exactly one instance of the message
    expect(screen.getAllByText('Already here')).toHaveLength(1)
  })

  it('updates read status on read_receipt', async () => {
    mockApiClient.get.mockResolvedValue({
      data: [
        {
          id: 3,
          conversation_id: 5,
          sender_id: 42,
          content: 'Did you read this?',
          sent_at: '2026-01-15T10:00:00Z',
          is_read: false,
        },
      ],
    })

    renderPage()

    await screen.findByText('Did you read this?')
    // Initially shows "Sent"
    expect(screen.getByText(/· Sent/)).toBeInTheDocument()

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'read_receipt',
        message_ids: [3],
        reader_id: 99,
      })
    })

    await waitFor(() => {
      expect(screen.getByText(/· Read/)).toBeInTheDocument()
    })
  })

  it('connects WebSocket to the correct URL', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })

    renderPage('7')

    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))
    expect(MockWebSocket.instances[0].url).toContain('/ws/chat/7')
  })

  it('fetches messages for the correct conversation', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })

    renderPage('12')

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenCalledWith('/conversations/12/messages')
    })
  })

  it('shows Seen by name when read_receipt includes reader_display_name', async () => {
    mockApiClient.get.mockResolvedValue({
      data: [
        {
          id: 7,
          conversation_id: 5,
          sender_id: 42,
          content: 'Will you see this?',
          sent_at: '2026-01-15T10:00:00Z',
          is_read: false,
        },
      ],
    })

    renderPage()

    await screen.findByText('Will you see this?')
    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'read_receipt',
        message_ids: [7],
        reader_id: 99,
        reader_display_name: 'Wolfy',
      })
    })

    await waitFor(() => {
      expect(screen.getByText('Seen by Wolfy')).toBeInTheDocument()
    })
  })

  it('does not show Seen by for own read_receipt (reader_id equals current user)', async () => {
    mockApiClient.get.mockResolvedValue({
      data: [
        {
          id: 8,
          conversation_id: 5,
          sender_id: 99,
          content: 'Message from other',
          sent_at: '2026-01-15T10:00:00Z',
          is_read: false,
        },
      ],
    })

    renderPage()

    await screen.findByText('Message from other')
    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'read_receipt',
        message_ids: [8],
        reader_id: 42, // same as mockUser.id
        reader_display_name: 'Foxy',
      })
    })

    // Give React time to process state update
    await waitFor(() => {
      expect(screen.queryByText('Seen by Foxy')).not.toBeInTheDocument()
    })
  })

  it('shows Seen by on the last message in the read_receipt batch', async () => {
    mockApiClient.get.mockResolvedValue({
      data: [
        {
          id: 2,
          conversation_id: 5,
          sender_id: 42,
          content: 'Second message',
          sent_at: '2026-01-15T10:01:00Z',
          is_read: false,
        },
        {
          id: 1,
          conversation_id: 5,
          sender_id: 42,
          content: 'First message',
          sent_at: '2026-01-15T10:00:00Z',
          is_read: false,
        },
      ],
    })

    renderPage()

    await screen.findByText('First message')
    await waitFor(() => expect(MockWebSocket.instances).toHaveLength(1))

    act(() => {
      MockWebSocket.instances[0].simulateMessage({
        type: 'read_receipt',
        message_ids: [1, 2],
        reader_id: 99,
        reader_display_name: 'Foxie',
      })
    })

    await waitFor(() => {
      expect(screen.getByText('Seen by Foxie')).toBeInTheDocument()
    })

    // "Seen by" should appear next to the last message (id=2, "Second message")
    const secondMsg = screen.getByText('Second message').closest('div.flex.flex-col')
    expect(secondMsg).toContainElement(screen.getByText('Seen by Foxie'))
  })
})
