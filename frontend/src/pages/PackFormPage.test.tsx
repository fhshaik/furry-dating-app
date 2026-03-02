import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import PackFormPage from './PackFormPage'

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: vi.fn(() => mockNavigate) }
})

import apiClient from '../lib/apiClient'

const mockApiClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  patch: ReturnType<typeof vi.fn>
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
}

function renderCreatePage() {
  return render(
    <MemoryRouter initialEntries={['/packs/new']}>
      <Routes>
        <Route path="/packs/new" element={<PackFormPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

function renderEditPage() {
  return render(
    <MemoryRouter initialEntries={['/packs/44/edit']}>
      <Routes>
        <Route path="/packs/:packId/edit" element={<PackFormPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PackFormPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('creates a pack and normalizes optional fields', async () => {
    mockApiClient.post.mockResolvedValue({ data: { ...packResponse, id: 88 } })
    const user = userEvent.setup()

    renderCreatePage()

    await user.type(screen.getByLabelText(/pack name/i), 'Sun Pack')
    await user.type(screen.getByLabelText(/description/i), ' Day hikes and brunch.')
    await user.type(screen.getByLabelText(/image url/i), ' https://example.com/sun-pack.jpg ')
    await user.clear(screen.getByLabelText(/maximum size/i))
    await user.type(screen.getByLabelText(/maximum size/i), '12')
    await user.type(screen.getByLabelText(/species tags/i), 'Wolf,  Fox , Hyena')
    await user.click(screen.getByLabelText(/require consensus/i))
    await user.click(screen.getByRole('button', { name: /create pack/i }))

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/packs', {
        name: 'Sun Pack',
        description: 'Day hikes and brunch.',
        image_url: 'https://example.com/sun-pack.jpg',
        species_tags: ['Wolf', 'Fox', 'Hyena'],
        max_size: 12,
        consensus_required: true,
        is_open: true,
      })
    })

    expect(mockNavigate).toHaveBeenCalledWith('/packs/88')
  })

  it('loads an existing pack and saves edits', async () => {
    mockApiClient.get.mockResolvedValue({ data: packResponse })
    mockApiClient.patch.mockResolvedValue({ data: packResponse })
    const user = userEvent.setup()

    renderEditPage()

    expect(await screen.findByDisplayValue('Moon Pack')).toBeInTheDocument()
    expect(screen.getByLabelText(/species tags/i)).toHaveValue('Wolf, Fox')
    expect(screen.getByLabelText(/require consensus/i)).toBeChecked()

    const nameInput = screen.getByLabelText(/pack name/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'Moon Pack Collective')
    await user.click(screen.getByRole('button', { name: /edit pack/i }))

    await waitFor(() => {
      expect(mockApiClient.patch).toHaveBeenCalledWith('/packs/44', {
        name: 'Moon Pack Collective',
        description: 'Late-night hikes and shared den movie marathons.',
        image_url: 'https://example.com/moon-pack.jpg',
        species_tags: ['Wolf', 'Fox'],
        max_size: 6,
        consensus_required: true,
        is_open: true,
      })
    })

    expect(mockNavigate).toHaveBeenCalledWith('/packs/44')
  })

  it('shows a load error when the pack cannot be fetched for editing', async () => {
    mockApiClient.get.mockRejectedValue(new Error('boom'))

    renderEditPage()

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to load pack details.')
  })

  it('shows a save error when create fails', async () => {
    mockApiClient.post.mockRejectedValue(new Error('boom'))
    const user = userEvent.setup()

    renderCreatePage()

    await user.type(screen.getByLabelText(/pack name/i), 'Sun Pack')
    await user.click(screen.getByRole('button', { name: /create pack/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Failed to create pack.')
  })
})
