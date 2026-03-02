import { useEffect, useState } from 'react'
import apiClient from '../lib/apiClient'
import FursonaFormModal from '../components/FursonaFormModal'
import type { Fursona } from '../components/fursonaForm'

const MAX_FURSONAS = 5

export default function FursonaManagerPage() {
  const [fursonas, setFursonas] = useState<Fursona[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [editingFursona, setEditingFursona] = useState<Fursona | undefined>()
  const [isFormOpen, setIsFormOpen] = useState(false)
  const hasReachedFursonaLimit = fursonas.length >= MAX_FURSONAS

  useEffect(() => {
    apiClient
      .get<Fursona[]>('/fursonas')
      .then((res) => setFursonas(res.data))
      .catch(() => setError('Failed to load fursonas.'))
      .finally(() => setLoading(false))
  }, [])

  async function handleSetPrimary(id: number) {
    setActionError(null)
    try {
      const res = await apiClient.post<Fursona>(`/fursonas/${id}/primary`)
      setFursonas((prev) =>
        prev.map((f) => ({ ...f, is_primary: f.id === res.data.id })),
      )
    } catch {
      setActionError('Failed to set primary fursona. Please try again.')
    }
  }

  async function handleDelete(id: number) {
    setActionError(null)
    try {
      await apiClient.delete(`/fursonas/${id}`)
      setFursonas((prev) => prev.filter((f) => f.id !== id))
    } catch {
      setActionError('Failed to delete fursona. Please try again.')
    }
  }

  function openCreateForm() {
    if (hasReachedFursonaLimit) {
      return
    }
    setEditingFursona(undefined)
    setActionError(null)
    setIsFormOpen(true)
  }

  function openEditForm(fursona: Fursona) {
    setEditingFursona(fursona)
    setActionError(null)
    setIsFormOpen(true)
  }

  function closeForm() {
    setEditingFursona(undefined)
    setIsFormOpen(false)
  }

  function handleSaved(savedFursona: Fursona) {
    setFursonas((prev) => {
      const next = prev.some((fursona) => fursona.id === savedFursona.id)
        ? prev.map((fursona) => (fursona.id === savedFursona.id ? savedFursona : fursona))
        : [savedFursona, ...prev]

      if (!savedFursona.is_primary) {
        return next
      }

      return next.map((fursona) => ({
        ...fursona,
        is_primary: fursona.id === savedFursona.id,
      }))
    })
    closeForm()
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <p className="text-gray-500">Loading fursonas...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-10">
        <p className="text-red-600">{error}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold text-gray-900">My Fursonas</h1>
        <button
          type="button"
          onClick={openCreateForm}
          disabled={hasReachedFursonaLimit}
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-300"
        >
          Add Fursona
        </button>
      </div>

      {hasReachedFursonaLimit && (
        <p className="mb-4 text-sm text-gray-600">
          You can have up to {MAX_FURSONAS} fursonas. Delete one to add another.
        </p>
      )}

      {actionError && <p className="mb-4 text-sm text-red-600">{actionError}</p>}

      {fursonas.length === 0 ? (
        <p className="text-gray-500">You have no fursonas yet.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {fursonas.map((fursona) => (
            <li
              key={fursona.id}
              className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-base font-semibold text-gray-900">{fursona.name}</span>
                    <span className="text-sm text-gray-500">{fursona.species}</span>
                    {fursona.is_primary && (
                      <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
                        Primary
                      </span>
                    )}
                    {fursona.is_nsfw && (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                        NSFW
                      </span>
                    )}
                  </div>
                  {fursona.description && (
                    <p className="mt-1 text-sm text-gray-600 truncate">{fursona.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={() => openEditForm(fursona)}
                    className="rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => handleSetPrimary(fursona.id)}
                    disabled={fursona.is_primary}
                    className="rounded-md border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:border-gray-200 disabled:text-gray-400 disabled:hover:bg-white"
                  >
                    Set as Primary
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(fursona.id)}
                    className="rounded-md border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {isFormOpen && (
        <FursonaFormModal
          fursona={editingFursona}
          onClose={closeForm}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}
