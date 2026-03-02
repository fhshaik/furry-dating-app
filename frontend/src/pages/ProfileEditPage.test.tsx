import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import ProfileEditPage from './ProfileEditPage'
import type { User } from '../contexts/AuthContext'

vi.mock('../lib/apiClient', () => ({
  default: {
    patch: vi.fn(),
  },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: vi.fn(() => vi.fn()) }
})

import apiClient from '../lib/apiClient'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

const mockApiClient = apiClient as unknown as { patch: ReturnType<typeof vi.fn> }
const mockUseAuth = useAuth as ReturnType<typeof vi.fn>
const mockUseNavigate = useNavigate as ReturnType<typeof vi.fn>

const mockUser: User = {
  id: 1,
  oauth_provider: 'google',
  email: 'test@example.com',
  display_name: 'Test User',
  bio: 'My bio',
  age: 25,
  city: 'Portland',
  nsfw_enabled: false,
  relationship_style: 'polyamorous',
  created_at: '2024-01-01T00:00:00Z',
}

function renderPage() {
  return render(
    <MemoryRouter>
      <ProfileEditPage />
    </MemoryRouter>,
  )
}

describe('ProfileEditPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseAuth.mockReturnValue({ user: mockUser, loading: false, logout: vi.fn() })
    mockUseNavigate.mockReturnValue(vi.fn())
  })

  it('renders the Edit Profile heading', () => {
    renderPage()
    expect(screen.getByRole('heading', { name: /edit profile/i })).toBeInTheDocument()
  })

  it('pre-populates display name from current user', () => {
    renderPage()
    expect(screen.getByLabelText(/display name/i)).toHaveValue('Test User')
  })

  it('pre-populates bio from current user', () => {
    renderPage()
    expect(screen.getByLabelText(/bio/i)).toHaveValue('My bio')
  })

  it('pre-populates age from current user', () => {
    renderPage()
    expect(screen.getByLabelText(/^age$/i)).toHaveValue(25)
  })

  it('pre-populates city from current user', () => {
    renderPage()
    expect(screen.getByLabelText(/city/i)).toHaveValue('Portland')
  })

  it('pre-populates relationship style from current user', () => {
    renderPage()
    expect(screen.getByLabelText(/relationship style/i)).toHaveValue('polyamorous')
  })

  it('renders empty fields when user has null values', () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, bio: null, age: null, city: null, relationship_style: null },
      loading: false,
      logout: vi.fn(),
    })
    renderPage()
    expect(screen.getByLabelText(/bio/i)).toHaveValue('')
    expect(screen.getByLabelText(/city/i)).toHaveValue('')
    expect(screen.getByLabelText(/relationship style/i)).toHaveValue('')
  })

  it('renders Save and Cancel buttons', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
  })

  it('shows all relationship style options', () => {
    renderPage()
    const select = screen.getByLabelText(/relationship style/i)
    const options = Array.from(select.querySelectorAll('option')).map((o) => o.value)
    expect(options).toContain('monogamous')
    expect(options).toContain('polyamorous')
    expect(options).toContain('open')
    expect(options).toContain('casual')
    expect(options).toContain('unsure')
  })

  it('submits the form with correct payload', async () => {
    mockApiClient.patch.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage()

    const displayNameInput = screen.getByLabelText(/display name/i)
    await user.clear(displayNameInput)
    await user.type(displayNameInput, 'New Name')

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(mockApiClient.patch).toHaveBeenCalledWith(
        '/users/me',
        expect.objectContaining({ display_name: 'New Name' }),
      )
    })
  })

  it('shows success message after successful save', async () => {
    mockApiClient.patch.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(screen.getByText(/profile saved successfully/i)).toBeInTheDocument()
    })
  })

  it('shows error message when save fails', async () => {
    mockApiClient.patch.mockRejectedValue(new Error('500'))
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(screen.getByText(/failed to save profile/i)).toBeInTheDocument()
    })
  })

  it('sends null for empty optional fields', async () => {
    mockApiClient.patch.mockResolvedValue({})
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, bio: null, age: null, city: null, relationship_style: null },
      loading: false,
      logout: vi.fn(),
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(mockApiClient.patch).toHaveBeenCalledWith(
        '/users/me',
        expect.objectContaining({ bio: null, age: null, city: null, relationship_style: null }),
      )
    })
  })

  it('disables Save button while submitting', async () => {
    let resolve: (v: unknown) => void
    mockApiClient.patch.mockReturnValue(new Promise((res) => { resolve = res }))
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /save/i }))

    expect(screen.getByRole('button', { name: /saving/i })).toBeDisabled()

    // Resolve to avoid unhandled promise
    resolve!({})
  })

  it('calls navigate(-1) when Cancel is clicked', async () => {
    const mockNavigate = vi.fn()
    mockUseNavigate.mockReturnValue(mockNavigate)
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /cancel/i }))

    expect(mockNavigate).toHaveBeenCalledWith(-1)
  })

  // NSFW toggle tests

  it('renders NSFW toggle unchecked when user.nsfw_enabled is false', () => {
    renderPage()
    expect(screen.getByLabelText(/enable nsfw content/i)).not.toBeChecked()
  })

  it('renders NSFW toggle checked when user.nsfw_enabled is true', () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, nsfw_enabled: true },
      loading: false,
      logout: vi.fn(),
    })
    renderPage()
    expect(screen.getByLabelText(/enable nsfw content/i)).toBeChecked()
  })

  it('enables NSFW toggle directly when age is already 18+', async () => {
    const user = userEvent.setup()
    renderPage() // mockUser has age: 25

    await user.click(screen.getByLabelText(/enable nsfw content/i))

    expect(screen.getByLabelText(/enable nsfw content/i)).toBeChecked()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows age confirmation modal when enabling NSFW with no age set', async () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, age: null },
      loading: false,
      logout: vi.fn(),
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByLabelText(/enable nsfw content/i))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText(/age confirmation required/i)).toBeInTheDocument()
  })

  it('shows age confirmation modal when enabling NSFW with age under 18', async () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, age: 16 },
      loading: false,
      logout: vi.fn(),
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByLabelText(/enable nsfw content/i))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('does not enable NSFW toggle when modal is shown (toggle stays unchecked)', async () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, age: null },
      loading: false,
      logout: vi.fn(),
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByLabelText(/enable nsfw content/i))

    expect(screen.getByLabelText(/enable nsfw content/i)).not.toBeChecked()
  })

  it('closes modal and reverts toggle when Cancel is clicked in modal', async () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, age: null },
      loading: false,
      logout: vi.fn(),
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByLabelText(/enable nsfw content/i))
    expect(screen.getByRole('dialog')).toBeInTheDocument()

    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: /cancel/i }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByLabelText(/enable nsfw content/i)).not.toBeChecked()
  })

  it('shows error in modal when confirming with age under 18', async () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, age: null },
      loading: false,
      logout: vi.fn(),
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByLabelText(/enable nsfw content/i))

    const modalAgeInput = screen.getByLabelText(/your age/i)
    await user.type(modalAgeInput, '16')
    await user.click(screen.getByRole('button', { name: /confirm/i }))

    expect(screen.getByText(/you must be 18 or older/i)).toBeInTheDocument()
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('shows error in modal when confirming with empty age', async () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, age: null },
      loading: false,
      logout: vi.fn(),
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByLabelText(/enable nsfw content/i))
    await user.click(screen.getByRole('button', { name: /confirm/i }))

    expect(screen.getByText(/you must be 18 or older/i)).toBeInTheDocument()
  })

  it('enables NSFW and sets age after confirming valid age in modal', async () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, age: null },
      loading: false,
      logout: vi.fn(),
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByLabelText(/enable nsfw content/i))

    const modalAgeInput = screen.getByLabelText(/your age/i)
    await user.type(modalAgeInput, '21')
    await user.click(screen.getByRole('button', { name: /confirm/i }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByLabelText(/enable nsfw content/i)).toBeChecked()
    expect(screen.getByLabelText(/^age$/i)).toHaveValue(21)
  })

  it('includes nsfw_enabled in the submit payload', async () => {
    mockApiClient.patch.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage() // nsfw_enabled: false

    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(mockApiClient.patch).toHaveBeenCalledWith(
        '/users/me',
        expect.objectContaining({ nsfw_enabled: false }),
      )
    })
  })

  it('submits nsfw_enabled true after enabling toggle with valid age', async () => {
    mockApiClient.patch.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage() // age: 25

    await user.click(screen.getByLabelText(/enable nsfw content/i))
    await user.click(screen.getByRole('button', { name: /save/i }))

    await waitFor(() => {
      expect(mockApiClient.patch).toHaveBeenCalledWith(
        '/users/me',
        expect.objectContaining({ nsfw_enabled: true }),
      )
    })
  })

  it('disabling NSFW toggle works without modal', async () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockUser, nsfw_enabled: true, age: 25 },
      loading: false,
      logout: vi.fn(),
    })
    const user = userEvent.setup()
    renderPage()

    expect(screen.getByLabelText(/enable nsfw content/i)).toBeChecked()
    await user.click(screen.getByLabelText(/enable nsfw content/i))

    expect(screen.getByLabelText(/enable nsfw content/i)).not.toBeChecked()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
