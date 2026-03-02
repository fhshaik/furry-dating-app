import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../lib/apiClient'
import PackCard from '../components/PackCard'

interface MyPack {
  id: number
  name: string
  description: string | null
  image_url: string | null
  species_tags: string[] | null
  max_size: number
  is_open: boolean
  member_count: number
  created_at: string
  conversation_id: number | null
}

interface MyPacksResponse {
  items: MyPack[]
  page: number
  limit: number
  total: number
  has_more: boolean
}

export default function MyPacksPage() {
  const [packs, setPacks] = useState<MyPack[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    setLoading(true)
    setError(null)

    apiClient
      .get<MyPacksResponse>('/packs/mine')
      .then((response) => {
        if (!isMounted) {
          return
        }
        setPacks(response.data.items)
      })
      .catch(() => {
        if (!isMounted) {
          return
        }
        setError('Failed to load your packs.')
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [])

  return (
    <section className="mx-auto flex min-h-full w-full max-w-5xl flex-col gap-6 px-4 py-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-orange-500">My Packs</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">Your Packs</h1>
        </div>
        <Link
          to="/packs/new"
          className="rounded-full bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600"
        >
          Create pack
        </Link>
      </div>

      {loading ? (
        <p className="rounded-2xl border border-gray-200 bg-white px-4 py-6 text-sm text-gray-600">
          Loading your packs...
        </p>
      ) : null}

      {!loading && error ? (
        <p
          role="alert"
          className="rounded-2xl border border-red-200 bg-red-50 px-4 py-6 text-sm text-red-700"
        >
          {error}
        </p>
      ) : null}

      {!loading && !error && packs.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-gray-300 bg-gray-50 px-6 py-12 text-center">
          <p className="text-lg font-semibold text-gray-900">You haven&apos;t joined any packs yet.</p>
          <p className="mt-2 text-sm text-gray-500">
            Discover open packs to join, or create your own.
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <Link
              to="/discover"
              className="rounded-full border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
            >
              Browse packs
            </Link>
            <Link
              to="/packs/new"
              className="rounded-full bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600"
            >
              Create pack
            </Link>
          </div>
        </div>
      ) : null}

      {!loading && !error && packs.length > 0 ? (
        <ul
          className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
          aria-label="My packs"
        >
          {packs.map((pack) => (
            <li key={pack.id}>
              <PackCard
                name={pack.name}
                imageUrl={pack.image_url}
                memberCount={pack.member_count}
                speciesTags={pack.species_tags}
                packId={pack.id}
                conversationId={pack.conversation_id}
              />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
