import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import apiClient from '../lib/apiClient'

interface PackPayload {
  name: string
  description: string | null
  image_url: string | null
  species_tags: string[] | null
  max_size: number
  consensus_required: boolean
  is_open: boolean
}

interface PackResponse extends PackPayload {
  id: number
  creator_id: number
  created_at: string
}

function normalizeSpeciesTags(value: string) {
  const tags = value
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)

  return tags.length > 0 ? tags : null
}

export default function PackFormPage() {
  const navigate = useNavigate()
  const { packId } = useParams<{ packId: string }>()
  const isEditMode = Boolean(packId)

  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [speciesTags, setSpeciesTags] = useState('')
  const [maxSize, setMaxSize] = useState('10')
  const [consensusRequired, setConsensusRequired] = useState(false)
  const [isOpen, setIsOpen] = useState(true)

  const [loading, setLoading] = useState(isEditMode)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isEditMode || !packId) {
      return
    }

    let isMounted = true

    setLoading(true)
    setError(null)

    apiClient
      .get<PackResponse>(`/packs/${packId}`)
      .then((response) => {
        if (!isMounted) {
          return
        }

        const pack = response.data
        setName(pack.name)
        setDescription(pack.description ?? '')
        setImageUrl(pack.image_url ?? '')
        setSpeciesTags(pack.species_tags?.join(', ') ?? '')
        setMaxSize(pack.max_size.toString())
        setConsensusRequired(pack.consensus_required)
        setIsOpen(pack.is_open)
      })
      .catch(() => {
        if (!isMounted) {
          return
        }

        setError('Failed to load pack details.')
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [isEditMode, packId])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)

    const payload: PackPayload = {
      name: name.trim(),
      description: description.trim() ? description.trim() : null,
      image_url: imageUrl.trim() ? imageUrl.trim() : null,
      species_tags: normalizeSpeciesTags(speciesTags),
      max_size: Number(maxSize),
      consensus_required: consensusRequired,
      is_open: isOpen,
    }

    try {
      const response = isEditMode
        ? await apiClient.patch<PackResponse>(`/packs/${packId}`, payload)
        : await apiClient.post<PackResponse>('/packs', payload)

      navigate(`/packs/${response.data.id}`)
    } catch {
      setError(isEditMode ? 'Failed to save pack changes.' : 'Failed to create pack.')
    } finally {
      setSubmitting(false)
    }
  }

  const heading = isEditMode ? 'Edit Pack' : 'Create Pack'
  const submitLabel = submitting ? (isEditMode ? 'Saving...' : 'Creating...') : heading
  const cancelHref = isEditMode && packId ? `/packs/${packId}` : '/packs'

  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-8">
      <div className="rounded-[2rem] border border-orange-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 border-b border-gray-200 pb-6 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-orange-500">
              Pack Management
            </p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">{heading}</h1>
            <p className="mt-2 text-sm text-gray-600">
              {isEditMode
                ? 'Update your pack details, membership settings, and species tags.'
                : 'Start a new pack with clear expectations for future members.'}
            </p>
          </div>
          <Link
            to={cancelHref}
            className="rounded-full border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
          >
            Cancel
          </Link>
        </div>

        {loading ? (
          <p className="mt-6 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-6 text-sm text-gray-600">
            Loading pack details...
          </p>
        ) : (
          <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
            <label className="block">
              <span className="text-sm font-semibold text-gray-900">Pack name</span>
              <input
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                className="mt-2 w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900"
              />
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-gray-900">Description</span>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={5}
                className="mt-2 w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900"
              />
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-gray-900">Image URL</span>
              <input
                type="url"
                value={imageUrl}
                onChange={(event) => setImageUrl(event.target.value)}
                placeholder="https://example.com/your-pack.jpg"
                className="mt-2 w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900"
              />
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-gray-900">Species tags</span>
              <input
                type="text"
                value={speciesTags}
                onChange={(event) => setSpeciesTags(event.target.value)}
                placeholder="Wolf, Fox, Hyena"
                className="mt-2 w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900"
              />
              <span className="mt-2 block text-xs text-gray-500">Separate tags with commas.</span>
            </label>

            <label className="block">
              <span className="text-sm font-semibold text-gray-900">Maximum size</span>
              <input
                type="number"
                min={1}
                value={maxSize}
                onChange={(event) => setMaxSize(event.target.value)}
                required
                className="mt-2 w-full rounded-2xl border border-gray-300 px-4 py-3 text-sm text-gray-900"
              />
            </label>

            <label className="flex items-start gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4">
              <input
                type="checkbox"
                checked={consensusRequired}
                onChange={(event) => setConsensusRequired(event.target.checked)}
                className="mt-1 h-4 w-4"
              />
              <span>
                <span className="block text-sm font-semibold text-gray-900">Require consensus</span>
                <span className="mt-1 block text-sm text-gray-600">
                  Every current member must approve join requests.
                </span>
              </span>
            </label>

            <label className="flex items-start gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-4">
              <input
                type="checkbox"
                checked={isOpen}
                onChange={(event) => setIsOpen(event.target.checked)}
                className="mt-1 h-4 w-4"
              />
              <span>
                <span className="block text-sm font-semibold text-gray-900">Open to join requests</span>
                <span className="mt-1 block text-sm text-gray-600">
                  Disable this if the pack should stay invite-only.
                </span>
              </span>
            </label>

            {error ? (
              <p role="alert" className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}
              </p>
            ) : null}

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={submitting}
                className="rounded-full bg-orange-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitLabel}
              </button>
              <Link
                to={cancelHref}
                className="rounded-full border border-gray-300 px-5 py-3 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
              >
                Back
              </Link>
            </div>
          </form>
        )}
      </div>
    </section>
  )
}
