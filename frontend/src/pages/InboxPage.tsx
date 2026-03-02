import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../lib/apiClient'

type ConversationType = 'direct' | 'pack'

interface ConversationItem {
  id: number
  type: ConversationType
  pack_id: number | null
  created_at: string
  unread_count: number
}

export default function InboxPage() {
  const [conversations, setConversations] = useState<ConversationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    apiClient
      .get<ConversationItem[]>('/conversations')
      .then((response) => {
        if (!isMounted) {
          return
        }
        setConversations(response.data)
        setError(null)
      })
      .catch(() => {
        if (!isMounted) {
          return
        }
        setConversations([])
        setError('Failed to load conversations.')
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

  function formatDate(isoString: string): string {
    return new Date(isoString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  return (
    <section className="mx-auto flex min-h-full w-full max-w-3xl flex-col gap-4 px-4 py-6">
      <div className="space-y-1">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Inbox</h1>
        <p className="text-sm text-gray-600">All your direct and pack conversations.</p>
      </div>

      {loading ? (
        <p className="rounded-2xl border border-gray-200 bg-white px-4 py-6 text-sm text-gray-600">
          Loading conversations...
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

      {!loading && !error && conversations.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-gray-300 bg-white px-6 py-10 text-center">
          <h2 className="text-lg font-semibold text-gray-900">No conversations yet.</h2>
          <p className="mt-2 text-sm text-gray-600">
            Match with someone or join a pack to start chatting.
          </p>
        </div>
      ) : null}

      {!loading && !error ? (
        <ul className="space-y-3" aria-label="Conversations">
          {conversations.map((conv) => (
            <li key={conv.id}>
              <Link
                to={`/inbox/${conv.id}`}
                className="flex items-center justify-between gap-4 rounded-3xl border border-gray-200 bg-white p-4 shadow-sm transition hover:border-indigo-200 hover:bg-indigo-50"
              >
                <div className="space-y-1">
                  <h2 className="text-base font-semibold text-gray-900">
                    {conv.type === 'pack' ? `Pack Chat` : 'Direct Message'}
                    {conv.pack_id != null ? ` #${conv.pack_id}` : ''}
                  </h2>
                  <p className="text-xs text-gray-500">Started {formatDate(conv.created_at)}</p>
                </div>
                <div className="flex items-center gap-2">
                  {conv.unread_count > 0 ? (
                    <span className="shrink-0 rounded-full bg-rose-100 px-3 py-1 text-xs font-semibold text-rose-700">
                      {conv.unread_count} unread
                    </span>
                  ) : null}
                  <span
                    className={`shrink-0 rounded-full px-3 py-1 text-xs font-medium uppercase tracking-wide ${
                      conv.type === 'pack'
                        ? 'bg-indigo-100 text-indigo-700'
                        : 'bg-green-100 text-green-700'
                    }`}
                  >
                    {conv.type === 'pack' ? 'Pack' : 'Direct'}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
