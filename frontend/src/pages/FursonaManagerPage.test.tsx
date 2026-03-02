import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import FursonaManagerPage from './FursonaManagerPage'

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

import apiClient from '../lib/apiClient'

const mockApiClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  patch: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}

const mockFursonas = [
  {
    id: 1,
    name: 'Blaze',
    species: 'Wolf',
    description: 'A fiery wolf',
    image_url: null,
    is_primary: true,
    is_nsfw: false,
    created_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 2,
    name: 'Shadow',
    species: 'Fox',
    description: null,
    image_url: null,
    is_primary: false,
    is_nsfw: true,
    created_at: '2024-01-02T00:00:00Z',
  },
]

const fursonaAtLimit = Array.from({ length: 5 }, (_, index) => ({
  id: index + 1,
  name: `Fursona ${index + 1}`,
  species: 'Wolf',
  description: null,
  image_url: null,
  is_primary: index === 0,
  is_nsfw: false,
  created_at: `2024-01-0${index + 1}T00:00:00Z`,
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <FursonaManagerPage />
    </MemoryRouter>,
  )
}

describe('FursonaManagerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApiClient.get.mockResolvedValue({ data: mockFursonas })
  })

  it('renders the My Fursonas heading', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /my fursonas/i })).toBeInTheDocument()
    })
  })

  it('shows loading state initially', () => {
    mockApiClient.get.mockReturnValue(new Promise(() => {}))
    renderPage()
    expect(screen.getByText(/loading fursonas/i)).toBeInTheDocument()
  })

  it('renders list of fursonas after loading', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Blaze')).toBeInTheDocument()
      expect(screen.getByText('Shadow')).toBeInTheDocument()
    })
  })

  it('shows species for each fursona', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Wolf')).toBeInTheDocument()
      expect(screen.getByText('Fox')).toBeInTheDocument()
    })
  })

  it('shows Primary badge for the primary fursona', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('Primary')).toBeInTheDocument()
    })
  })

  it('shows NSFW badge for NSFW fursonas', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('NSFW')).toBeInTheDocument()
    })
  })

  it('shows description when present', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('A fiery wolf')).toBeInTheDocument()
    })
  })

  it('shows Set as Primary button on every fursona card and disables it for the primary fursona', async () => {
    renderPage()
    await waitFor(() => {
      const setPrimaryButtons = screen.getAllByRole('button', { name: /set as primary/i })
      expect(setPrimaryButtons).toHaveLength(2)
      expect(setPrimaryButtons[0]).toBeDisabled()
      expect(setPrimaryButtons[1]).toBeEnabled()
    })
  })

  it('shows Delete button for each fursona', async () => {
    renderPage()
    await waitFor(() => {
      const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
      expect(deleteButtons).toHaveLength(2)
    })
  })

  it('opens the create form from the add fursona button', async () => {
    const user = userEvent.setup()
    mockApiClient.get
      .mockResolvedValueOnce({ data: mockFursonas })
      .mockResolvedValueOnce({ data: [{ id: 1, name: 'Wolf', slug: 'wolf' }] })
    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add fursona/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /add fursona/i }))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /new fursona/i })).toBeInTheDocument()
  })

  it('disables adding a fursona after reaching the 5-fursona limit', async () => {
    mockApiClient.get.mockResolvedValue({ data: fursonaAtLimit })
    const user = userEvent.setup()
    renderPage()

    const addButton = await screen.findByRole('button', { name: /add fursona/i })
    expect(addButton).toBeDisabled()
    expect(
      screen.getByText(/you can have up to 5 fursonas\. delete one to add another\./i),
    ).toBeInTheDocument()

    await user.click(addButton)

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('opens the edit form with fursona values populated', async () => {
    const user = userEvent.setup()
    mockApiClient.get
      .mockResolvedValueOnce({ data: mockFursonas })
      .mockResolvedValueOnce({ data: [{ id: 1, name: 'Wolf', slug: 'wolf' }] })
    renderPage()

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /edit/i })).toHaveLength(2)
    })

    await user.click(screen.getAllByRole('button', { name: /edit/i })[0])

    expect(screen.getByLabelText(/name/i)).toHaveValue('Blaze')
    expect(screen.getByLabelText(/species/i)).toHaveValue('Wolf')
  })

  it('adds a created fursona to the list after save', async () => {
    const createdFursona = {
      id: 3,
      name: 'Nova',
      species: 'Dragon',
      traits: ['playful'],
      description: 'A bright dragon',
      image_url: null,
      is_primary: false,
      is_nsfw: false,
      created_at: '2024-01-03T00:00:00Z',
    }
    mockApiClient.get
      .mockResolvedValueOnce({ data: mockFursonas })
      .mockResolvedValueOnce({
        data: [
          { id: 1, name: 'Dragon', slug: 'dragon' },
          { id: 2, name: 'Wolf', slug: 'wolf' },
        ],
      })
    mockApiClient.post.mockResolvedValue({ data: createdFursona })
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add fursona/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /add fursona/i }))
    await user.type(screen.getByLabelText(/name/i), 'Nova')
    await user.selectOptions(screen.getByLabelText(/species/i), 'Dragon')
    await user.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/fursonas',
        expect.objectContaining({
          name: 'Nova',
          species: 'Dragon',
        }),
      )
      expect(screen.getByText('Nova')).toBeInTheDocument()
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
  })

  it('updates an existing fursona after edit save', async () => {
    const updatedFursona = {
      ...mockFursonas[1],
      name: 'Shadowfang',
      species: 'Fox',
      traits: ['protective'],
      description: 'Updated fox',
    }
    mockApiClient.get
      .mockResolvedValueOnce({ data: mockFursonas })
      .mockResolvedValueOnce({
        data: [
          { id: 1, name: 'Fox', slug: 'fox' },
          { id: 2, name: 'Wolf', slug: 'wolf' },
        ],
      })
    mockApiClient.patch.mockResolvedValue({ data: updatedFursona })
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /edit/i })).toHaveLength(2)
    })

    await user.click(screen.getAllByRole('button', { name: /edit/i })[1])
    const nameInput = screen.getByLabelText(/name/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'Shadowfang')
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(mockApiClient.patch).toHaveBeenCalledWith(
        '/fursonas/2',
        expect.objectContaining({ name: 'Shadowfang' }),
      )
      expect(screen.getByText('Shadowfang')).toBeInTheDocument()
      expect(screen.queryByText('Shadow')).not.toBeInTheDocument()
    })
  })

  it('shows empty state when there are no fursonas', async () => {
    mockApiClient.get.mockResolvedValue({ data: [] })
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/you have no fursonas yet/i)).toBeInTheDocument()
    })
  })

  it('shows error message when loading fails', async () => {
    mockApiClient.get.mockRejectedValue(new Error('Network error'))
    renderPage()
    await waitFor(() => {
      expect(screen.getByText(/failed to load fursonas/i)).toBeInTheDocument()
    })
  })

  it('removes fursona from list after successful delete', async () => {
    mockApiClient.delete.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => {
      expect(screen.getByText('Shadow')).toBeInTheDocument()
    })

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    await user.click(deleteButtons[1]) // Delete Shadow (index 1)

    await waitFor(() => {
      expect(screen.queryByText('Shadow')).not.toBeInTheDocument()
      expect(screen.getByText('Blaze')).toBeInTheDocument()
    })
  })

  it('re-enables adding a fursona after deleting from the 5-fursona limit', async () => {
    mockApiClient.get.mockResolvedValue({ data: fursonaAtLimit })
    mockApiClient.delete.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage()

    const addButton = await screen.findByRole('button', { name: /add fursona/i })
    expect(addButton).toBeDisabled()

    await user.click(screen.getAllByRole('button', { name: /delete/i })[4])

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /add fursona/i })).toBeEnabled()
      expect(
        screen.queryByText(/you can have up to 5 fursonas\. delete one to add another\./i),
      ).not.toBeInTheDocument()
    })
  })

  it('calls delete API with the correct fursona id', async () => {
    mockApiClient.delete.mockResolvedValue({})
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /delete/i })).toHaveLength(2)
    })

    const deleteButtons = screen.getAllByRole('button', { name: /delete/i })
    await user.click(deleteButtons[0]) // Delete Blaze (id: 1)

    await waitFor(() => {
      expect(mockApiClient.delete).toHaveBeenCalledWith('/fursonas/1')
    })
  })

  it('shows action error when delete fails', async () => {
    mockApiClient.delete.mockRejectedValue(new Error('500'))
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /delete/i })).toHaveLength(2)
    })

    await user.click(screen.getAllByRole('button', { name: /delete/i })[0])

    await waitFor(() => {
      expect(screen.getByText(/failed to delete fursona/i)).toBeInTheDocument()
    })
  })

  it('updates primary fursona after set primary', async () => {
    const updatedFursona = { ...mockFursonas[1], is_primary: true }
    mockApiClient.post.mockResolvedValue({ data: updatedFursona })
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /set as primary/i })).toHaveLength(2)
    })

    await user.click(screen.getAllByRole('button', { name: /set as primary/i })[1])

    await waitFor(() => {
      const primaryBadges = screen.getAllByText('Primary')
      expect(primaryBadges).toHaveLength(1)
      // Shadow (id 2) is now primary; Blaze (id 1) is no longer primary
      const setPrimaryButtons = screen.getAllByRole('button', { name: /set as primary/i })
      expect(setPrimaryButtons).toHaveLength(2)
      expect(setPrimaryButtons[0]).toBeEnabled()
      expect(setPrimaryButtons[1]).toBeDisabled()
    })
  })

  it('calls set primary API with the correct fursona id', async () => {
    const updatedFursona = { ...mockFursonas[1], is_primary: true }
    mockApiClient.post.mockResolvedValue({ data: updatedFursona })
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /set as primary/i })).toHaveLength(2)
    })

    await user.click(screen.getAllByRole('button', { name: /set as primary/i })[1])

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/fursonas/2/primary')
    })
  })

  it('shows action error when set primary fails', async () => {
    mockApiClient.post.mockRejectedValue(new Error('500'))
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /set as primary/i })).toHaveLength(2)
    })

    await user.click(screen.getAllByRole('button', { name: /set as primary/i })[1])

    await waitFor(() => {
      expect(screen.getByText(/failed to set primary fursona/i)).toBeInTheDocument()
    })
  })
})
