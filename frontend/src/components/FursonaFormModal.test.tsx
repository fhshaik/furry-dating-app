import axios from 'axios'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import FursonaFormModal from './FursonaFormModal'

vi.mock('../lib/apiClient', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('axios', () => ({
  default: {
    put: vi.fn(),
  },
}))

import apiClient from '../lib/apiClient'

const mockApiClient = apiClient as unknown as {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  patch: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}
const mockAxios = axios as unknown as {
  put: ReturnType<typeof vi.fn>
}

const speciesOptions = [
  { id: 1, name: 'Fox', slug: 'fox' },
  { id: 2, name: 'Wolf', slug: 'wolf' },
]

describe('FursonaFormModal', () => {
  const createObjectURL = vi.fn(() => 'blob:fursona-preview')
  const revokeObjectURL = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockApiClient.get.mockResolvedValue({ data: speciesOptions })
    mockAxios.put.mockResolvedValue({})
    URL.createObjectURL = createObjectURL
    URL.revokeObjectURL = revokeObjectURL
  })

  it('loads species options for the dropdown', async () => {
    render(<FursonaFormModal onClose={vi.fn()} onSaved={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Fox' })).toBeInTheDocument()
      expect(screen.getByRole('option', { name: 'Wolf' })).toBeInTheDocument()
    })
  })

  it('submits create payload with selected traits and trimmed description', async () => {
    const onSaved = vi.fn()
    const savedFursona = {
      id: 1,
      name: 'Nova',
      species: 'Fox',
      traits: ['playful'],
      description: 'Bright and curious',
      image_url: null,
      is_primary: false,
      is_nsfw: false,
      created_at: '2024-01-01T00:00:00Z',
    }
    mockApiClient.post.mockResolvedValue({ data: savedFursona })
    const user = userEvent.setup()

    render(<FursonaFormModal onClose={vi.fn()} onSaved={onSaved} />)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Fox' })).toBeInTheDocument()
    })

    await user.type(screen.getByLabelText(/name/i), '  Nova  ')
    await user.selectOptions(screen.getByLabelText(/species/i), 'Fox')
    const traitsGroup = screen.getByLabelText(/traits/i)
    await user.click(within(traitsGroup).getByRole('button', { name: 'playful' }))
    await user.type(screen.getByLabelText(/description/i), '  Bright and curious  ')
    await user.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/fursonas', {
        name: 'Nova',
        species: 'Fox',
        traits: ['playful'],
        description: 'Bright and curious',
        image_url: null,
        is_primary: false,
        is_nsfw: false,
      })
      expect(onSaved).toHaveBeenCalledWith(savedFursona)
    })
  })

  it('submits update payload when editing an existing fursona', async () => {
    const fursona = {
      id: 3,
      name: 'Blaze',
      species: 'Wolf',
      traits: ['adventurous'],
      description: 'A bold wolf',
      image_url: null,
      is_primary: false,
      is_nsfw: false,
      created_at: '2024-01-01T00:00:00Z',
    }
    mockApiClient.patch.mockResolvedValue({ data: { ...fursona, name: 'Blazestar' } })
    const user = userEvent.setup()

    render(<FursonaFormModal fursona={fursona} onClose={vi.fn()} onSaved={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByLabelText(/name/i)).toHaveValue('Blaze')
    })

    const nameInput = screen.getByLabelText(/name/i)
    await user.clear(nameInput)
    await user.type(nameInput, 'Blazestar')
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(mockApiClient.patch).toHaveBeenCalledWith(
        '/fursonas/3',
        expect.objectContaining({ name: 'Blazestar' }),
      )
    })
  })

  it('does not submit when required fields are missing', async () => {
    const user = userEvent.setup()
    render(<FursonaFormModal onClose={vi.fn()} onSaved={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: /^create$/i }))

    expect(mockApiClient.post).not.toHaveBeenCalled()
  })

  it('uploads a selected image before updating an existing fursona', async () => {
    const onSaved = vi.fn()
    const fursona = {
      id: 7,
      name: 'Blaze',
      species: 'Wolf',
      traits: null,
      description: null,
      image_url: null,
      is_primary: false,
      is_nsfw: false,
      created_at: '2024-01-01T00:00:00Z',
    }
    const uploadResponse = {
      upload_url: 'https://bucket.s3.amazonaws.com/upload',
      key: 'fursonas/7/file',
      public_url: 'https://bucket.s3.amazonaws.com/fursonas/7/file',
    }
    mockApiClient.get
      .mockResolvedValueOnce({ data: speciesOptions })
      .mockResolvedValueOnce({ data: uploadResponse })
    mockApiClient.patch.mockResolvedValue({
      data: { ...fursona, image_url: uploadResponse.public_url },
    })
    const user = userEvent.setup()

    render(<FursonaFormModal fursona={fursona} onClose={vi.fn()} onSaved={onSaved} />)

    await waitFor(() => {
      expect(screen.getByLabelText(/name/i)).toHaveValue('Blaze')
    })

    const file = new File(['wolf'], 'wolf.png', { type: 'image/png' })
    await user.upload(screen.getByLabelText(/profile image/i), file)
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      expect(mockApiClient.get).toHaveBeenLastCalledWith('/fursonas/7/upload-url', {
        params: { content_type: 'image/png' },
      })
      expect(mockAxios.put).toHaveBeenCalledWith(uploadResponse.upload_url, file, {
        headers: { 'Content-Type': 'image/png' },
      })
      expect(mockApiClient.patch).toHaveBeenCalledWith('/fursonas/7', {
        name: 'Blaze',
        species: 'Wolf',
        traits: null,
        description: null,
        image_url: uploadResponse.public_url,
        is_primary: false,
        is_nsfw: false,
      })
      expect(onSaved).toHaveBeenCalledWith({
        ...fursona,
        image_url: uploadResponse.public_url,
      })
    })
  })

  it('shows an image preview after selecting a file', async () => {
    const user = userEvent.setup()
    render(<FursonaFormModal onClose={vi.fn()} onSaved={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Fox' })).toBeInTheDocument()
    })

    const file = new File(['fox'], 'fox.png', { type: 'image/png' })
    await user.upload(screen.getByLabelText(/profile image/i), file)

    const preview = screen.getByRole('img', { name: /fursona preview/i })
    expect(preview).toHaveAttribute('src', 'blob:fursona-preview')
    expect(createObjectURL).toHaveBeenCalledWith(file)
  })

  it('shows the existing fursona image before a new upload is selected', async () => {
    const fursona = {
      id: 7,
      name: 'Blaze',
      species: 'Wolf',
      traits: null,
      description: null,
      image_url: 'https://cdn.example.com/blaze.png',
      is_primary: false,
      is_nsfw: false,
      created_at: '2024-01-01T00:00:00Z',
    }

    render(<FursonaFormModal fursona={fursona} onClose={vi.fn()} onSaved={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByRole('img', { name: /blaze preview/i })).toHaveAttribute(
        'src',
        fursona.image_url,
      )
    })
    expect(createObjectURL).not.toHaveBeenCalled()
  })

  it('creates, uploads, and patches image_url for a new fursona', async () => {
    const onSaved = vi.fn()
    const createdFursona = {
      id: 11,
      name: 'Nova',
      species: 'Fox',
      traits: null,
      description: null,
      image_url: null,
      is_primary: false,
      is_nsfw: false,
      created_at: '2024-01-01T00:00:00Z',
    }
    const finalFursona = {
      ...createdFursona,
      image_url: 'https://bucket.s3.amazonaws.com/fursonas/11/file',
    }
    mockApiClient.get
      .mockResolvedValueOnce({ data: speciesOptions })
      .mockResolvedValueOnce({
        data: {
          upload_url: 'https://bucket.s3.amazonaws.com/upload',
          key: 'fursonas/11/file',
          public_url: finalFursona.image_url,
        },
      })
    mockApiClient.post.mockResolvedValue({ data: createdFursona })
    mockApiClient.patch.mockResolvedValue({ data: finalFursona })
    const user = userEvent.setup()

    render(<FursonaFormModal onClose={vi.fn()} onSaved={onSaved} />)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Fox' })).toBeInTheDocument()
    })

    await user.type(screen.getByLabelText(/name/i), 'Nova')
    await user.selectOptions(screen.getByLabelText(/species/i), 'Fox')
    const file = new File(['fox'], 'fox.png', { type: 'image/png' })
    await user.upload(screen.getByLabelText(/profile image/i), file)
    await user.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => {
      expect(mockApiClient.post).toHaveBeenCalledWith('/fursonas', {
        name: 'Nova',
        species: 'Fox',
        traits: null,
        description: null,
        image_url: null,
        is_primary: false,
        is_nsfw: false,
      })
      expect(mockApiClient.get).toHaveBeenLastCalledWith('/fursonas/11/upload-url', {
        params: { content_type: 'image/png' },
      })
      expect(mockAxios.put).toHaveBeenCalled()
      expect(mockApiClient.patch).toHaveBeenCalledWith('/fursonas/11', {
        image_url: finalFursona.image_url,
      })
      expect(onSaved).toHaveBeenCalledWith(finalFursona)
    })
  })

  it('rolls back a newly created fursona when image upload fails', async () => {
    const createdFursona = {
      id: 12,
      name: 'Nova',
      species: 'Fox',
      traits: null,
      description: null,
      image_url: null,
      is_primary: false,
      is_nsfw: false,
      created_at: '2024-01-01T00:00:00Z',
    }
    mockApiClient.get
      .mockResolvedValueOnce({ data: speciesOptions })
      .mockResolvedValueOnce({
        data: {
          upload_url: 'https://bucket.s3.amazonaws.com/upload',
          key: 'fursonas/12/file',
          public_url: 'https://bucket.s3.amazonaws.com/fursonas/12/file',
        },
      })
    mockApiClient.post.mockResolvedValue({ data: createdFursona })
    mockApiClient.delete.mockResolvedValue({})
    mockAxios.put.mockRejectedValue(new Error('upload failed'))
    const user = userEvent.setup()

    render(<FursonaFormModal onClose={vi.fn()} onSaved={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByRole('option', { name: 'Fox' })).toBeInTheDocument()
    })

    await user.type(screen.getByLabelText(/name/i), 'Nova')
    await user.selectOptions(screen.getByLabelText(/species/i), 'Fox')
    const file = new File(['fox'], 'fox.png', { type: 'image/png' })
    await user.upload(screen.getByLabelText(/profile image/i), file)
    await user.click(screen.getByRole('button', { name: /^create$/i }))

    await waitFor(() => {
      expect(mockApiClient.delete).toHaveBeenCalledWith('/fursonas/12')
      expect(screen.getByText(/failed to upload image/i)).toBeInTheDocument()
    })
  })
})
