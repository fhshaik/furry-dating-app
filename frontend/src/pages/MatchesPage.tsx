import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../lib/apiClient'

interface MatchUser {
  id: number
  display_name: string
  bio: string | null
  age: number | null
  city: string | null
  relationship_style: string | null
  created_at: string
}

interface MatchItem {
  id: number
  created_at: string
  matched_user: MatchUser
  last_message_preview: string | null
  conversation_id: number | null
}

export default function MatchesPage() {
  const [matches, setMatches] = useState<MatchItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    apiClient
      .get<MatchItem[]>('/matches')
      .then((response) => {
        if (!isMounted) {
          return
        }
        setMatches(response.data)
        setError(null)
      })
      .catch(() => {
        if (!isMounted) {
          return
        }
        setMatches([])
        setError('Failed to load matches.')
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
    <section className="mx-auto flex min-h-full w-full max-w-3xl flex-col gap-4 px-4 py-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Matches</h1>
        <p className="text-sm text-gray-600">All your 1:1 matches, with the latest conversation preview.</p>
      </div>

      {loading ? (
        <p className="rounded-2xl border border-gray-200 bg-white px-4 py-6 text-sm text-gray-600">
          Loading matches...
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

      {!loading && !error && matches.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-gray-300 bg-white px-6 py-10 text-center">
          <h2 className="text-lg font-semibold text-gray-900">You don&apos;t have any matches yet.</h2>
          <p className="mt-2 text-sm text-gray-600">Keep swiping to find someone worth messaging.</p>
        </div>
      ) : null}

      {!loading && !error ? (
        <ul className="space-y-3" aria-label="1:1 matches">
          {matches.map((match) => (
            <li
              key={match.id}
              id={`match-${match.id}`}
              className="scroll-mt-20 rounded-3xl border border-gray-200 bg-white p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1">
                  <h2 className="text-lg font-semibold text-gray-900">
                    {match.matched_user.display_name}
                    {typeof match.matched_user.age === 'number' ? `, ${match.matched_user.age}` : ''}
                  </h2>
                  <p className="text-sm text-gray-500">
                    {match.matched_user.city ?? 'Location hidden'}
                    {match.matched_user.relationship_style
                      ? ` • ${match.matched_user.relationship_style}`
                      : ''}
                  </p>
                </div>
                <p className="shrink-0 text-xs uppercase tracking-[0.2em] text-gray-400">1:1 Match</p>
              </div>

              <p className="mt-3 text-sm text-gray-600">
                {match.last_message_preview ?? 'No messages yet. Say hello to start the conversation.'}
              </p>

              {match.matched_user.bio ? (
                <p className="mt-3 line-clamp-2 text-sm text-gray-500">{match.matched_user.bio}</p>
              ) : null}

              {match.conversation_id != null ? (
                <div className="mt-4">
                  <Link
                    to={`/inbox/${match.conversation_id}`}
                    className="inline-flex items-center gap-2 rounded-full bg-indigo-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-600"
                  >
                    💬 Message
                  </Link>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
