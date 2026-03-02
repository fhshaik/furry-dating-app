import axios from 'axios'
import { useEffect, useState } from 'react'
import apiClient from '../lib/apiClient'
import { TRAITS } from './fursonaForm'
import type { Fursona } from './fursonaForm'

interface Species {
  id: number
  name: string
  slug: string
}

interface Props {
  fursona?: Fursona
  onClose: () => void
  onSaved: (fursona: Fursona) => void
}

interface UploadUrlResponse {
  upload_url: string
  key: string
  public_url: string
}

export default function FursonaFormModal({ fursona, onClose, onSaved }: Props) {
  const isEditing = Boolean(fursona)

  const [name, setName] = useState(fursona?.name ?? '')
  const [species, setSpecies] = useState(fursona?.species ?? '')
  const [traits, setTraits] = useState<string[]>(fursona?.traits ?? [])
  const [description, setDescription] = useState(fursona?.description ?? '')
  const [isPrimary, setIsPrimary] = useState(fursona?.is_primary ?? false)
  const [isNsfw, setIsNsfw] = useState(fursona?.is_nsfw ?? false)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(fursona?.image_url ?? null)

  const [speciesOptions, setSpeciesOptions] = useState<Species[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiClient
      .get<Species[]>('/species')
      .then((res) => setSpeciesOptions(res.data))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!imageFile) {
      setImagePreviewUrl(fursona?.image_url ?? null)
      return
    }

    const objectUrl = URL.createObjectURL(imageFile)
    setImagePreviewUrl(objectUrl)

    return () => {
      URL.revokeObjectURL(objectUrl)
    }
  }, [fursona?.image_url, imageFile])

  function toggleTrait(trait: string) {
    setTraits((prev) =>
      prev.includes(trait) ? prev.filter((t) => t !== trait) : [...prev, trait],
    )
  }

  async function uploadImage(fursonaId: number, file: File): Promise<string> {
    const contentType = file.type || 'application/octet-stream'
    const { data } = await apiClient.get<UploadUrlResponse>(`/fursonas/${fursonaId}/upload-url`, {
      params: { content_type: contentType },
    })
    await axios.put(data.upload_url, file, {
      headers: {
        'Content-Type': contentType,
      },
    })
    return data.public_url
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!name.trim()) {
      setError('Name is required.')
      return
    }
    if (!species) {
      setError('Species is required.')
      return
    }

    setSubmitting(true)

    const payload = {
      name: name.trim(),
      species,
      traits: traits.length > 0 ? traits : null,
      description: description.trim() || null,
      image_url: fursona?.image_url ?? null,
      is_primary: isPrimary,
      is_nsfw: isNsfw,
    }

    try {
      if (isEditing) {
        const imageUrl = imageFile ? await uploadImage(fursona!.id, imageFile) : payload.image_url
        const res = await apiClient.patch<Fursona>(`/fursonas/${fursona!.id}`, {
          ...payload,
          image_url: imageUrl,
        })
        onSaved(res.data)
        return
      }

      const createdResponse = await apiClient.post<Fursona>('/fursonas', payload)
      const createdFursona = createdResponse.data

      if (!imageFile) {
        onSaved(createdFursona)
        return
      }

      try {
        const imageUrl = await uploadImage(createdFursona.id, imageFile)
        const updatedResponse = await apiClient.patch<Fursona>(`/fursonas/${createdFursona.id}`, {
          image_url: imageUrl,
        })
        onSaved(updatedResponse.data)
      } catch {
        await apiClient.delete(`/fursonas/${createdFursona.id}`).catch(() => {})
        setError('Failed to upload image. Please try again.')
      }
    } catch {
      setError(`Failed to ${isEditing ? 'update' : 'create'} fursona. Please try again.`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="fursona-form-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
    >
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg max-h-[90vh] overflow-y-auto">
        <h2 id="fursona-form-title" className="text-lg font-semibold text-gray-900 mb-4">
          {isEditing ? 'Edit Fursona' : 'New Fursona'}
        </h2>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              className="block text-sm font-medium text-gray-700 mb-1"
              htmlFor="fursona-name"
            >
              Name
            </label>
            <input
              id="fursona-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label
              className="block text-sm font-medium text-gray-700 mb-1"
              htmlFor="fursona-species"
            >
              Species
            </label>
            <select
              id="fursona-species"
              value={species}
              onChange={(e) => setSpecies(e.target.value)}
              required
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">— select species —</option>
              {speciesOptions.map((s) => (
                <option key={s.id} value={s.name}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <span className="block text-sm font-medium text-gray-700 mb-2">Traits</span>
            <div className="flex flex-wrap gap-2" aria-label="Traits">
              {TRAITS.map((trait) => (
                <button
                  key={trait}
                  type="button"
                  onClick={() => toggleTrait(trait)}
                  aria-pressed={traits.includes(trait)}
                  className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                    traits.includes(trait)
                      ? 'bg-indigo-600 border-indigo-600 text-white'
                      : 'bg-white border-gray-300 text-gray-600 hover:border-indigo-400'
                  }`}
                >
                  {trait}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label
              className="block text-sm font-medium text-gray-700 mb-1"
              htmlFor="fursona-description"
            >
              Description
            </label>
            <textarea
              id="fursona-description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label
              className="block text-sm font-medium text-gray-700 mb-1"
              htmlFor="fursona-image"
            >
              Profile Image
            </label>
            <input
              id="fursona-image"
              type="file"
              accept="image/*"
              onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 file:mr-3 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-indigo-700"
            />
            {imagePreviewUrl && (
              <div className="mt-3">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
                  Image preview
                </p>
                <img
                  src={imagePreviewUrl}
                  alt={`${name.trim() || 'Fursona'} preview`}
                  className="h-40 w-full rounded-lg border border-gray-200 object-cover"
                />
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <input
              id="fursona-is-primary"
              type="checkbox"
              checked={isPrimary}
              onChange={(e) => setIsPrimary(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="fursona-is-primary" className="text-sm font-medium text-gray-700">
              Set as primary fursona
            </label>
          </div>

          <div className="flex items-center gap-3">
            <input
              id="fursona-is-nsfw"
              type="checkbox"
              checked={isNsfw}
              onChange={(e) => setIsNsfw(e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            <label htmlFor="fursona-is-nsfw" className="text-sm font-medium text-gray-700">
              NSFW fursona
            </label>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {submitting ? 'Saving...' : isEditing ? 'Save Changes' : 'Create'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
