import { useCallback, useEffect, useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import apiClient from '../lib/apiClient'
import { useAuth } from '../contexts/AuthContext'
import { useWebSocket } from '../hooks/useWebSocket'

interface Message {
  id: number
  conversation_id: number
  sender_id: number
  content: string
  sent_at: string
  is_read: boolean
}

function getWsUrl(conversationId: number): string {
  const apiBase = (import.meta.env['VITE_API_BASE_URL'] ?? '/api') as string
  try {
    const url = new URL(apiBase)
    const wsProto = url.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProto}//${url.host}/ws/chat/${conversationId}`
  } catch {
    const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    return `${wsProto}//${window.location.host}/ws/chat/${conversationId}`
  }
}

export default function ConversationViewPage() {
  const { conversationId } = useParams<{ conversationId: string }>()
  const { user } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [sendError, setSendError] = useState<string | null>(null)
  const [seenBy, setSeenBy] = useState<Map<number, { readerName: string; lastMessageId: number }>>(
    new Map(),
  )
  const bottomRef = useRef<HTMLDivElement | null>(null)

  const convId = conversationId ? parseInt(conversationId, 10) : null

  useEffect(() => {
    if (convId === null || isNaN(convId)) return
    let isMounted = true

    apiClient
      .get<Message[]>(`/conversations/${convId}/messages`)
      .then((res) => {
        if (!isMounted) return
        // API returns newest-first; reverse for chronological display
        setMessages(res.data.slice().reverse())
        setError(null)
      })
      .catch(() => {
        if (!isMounted) return
        setError('Failed to load messages.')
      })
      .finally(() => {
        if (isMounted) setLoading(false)
      })

    return () => {
      isMounted = false
    }
  }, [convId])

  const wsUrl = convId !== null && !isNaN(convId) ? getWsUrl(convId) : null

  const handleMessage = useCallback(
    (data: Record<string, unknown>) => {
      if (data['type'] === 'message') {
        const msg: Message = {
          id: data['id'] as number,
          conversation_id: data['conversation_id'] as number,
          sender_id: data['sender_id'] as number,
          content: data['content'] as string,
          sent_at: data['sent_at'] as string,
          is_read: data['is_read'] as boolean,
        }
        setMessages((prev) => {
          if (prev.some((m) => m.id === msg.id)) return prev
          return [...prev, msg]
        })
      } else if (data['type'] === 'read_receipt') {
        const readIds = data['message_ids'] as number[]
        const readIdSet = new Set<number>(readIds)
        setMessages((prev) =>
          prev.map((m) => (readIdSet.has(m.id) ? { ...m, is_read: true } : m)),
        )

        const readerId = data['reader_id'] as number
        const readerName = data['reader_display_name'] as string | undefined
        if (readerName && readerId !== user?.id) {
          const lastMessageId = Math.max(...readIds)
          setSeenBy((prev) => {
            const next = new Map(prev)
            next.set(readerId, { readerName, lastMessageId })
            return next
          })
        }
      }
    },
    [user?.id],
  )

  const { connected, reconnecting, send: wsSend } = useWebSocket(wsUrl, { onMessage: handleMessage })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = useCallback(() => {
    const content = input.trim()
    if (!content) return
    if (!connected) {
      setSendError('Not connected. Wait a moment and try again.')
      return
    }
    setSendError(null)
    wsSend(JSON.stringify({ content }))
    setInput('')
  }, [input, connected, wsSend])

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  function formatTime(isoString: string) {
    return new Date(isoString).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <section className="mx-auto flex min-h-full w-full max-w-3xl flex-col gap-4 px-4 py-6">
      <div className="flex items-center gap-3">
        <Link
          to="/inbox"
          className="rounded-full border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
        >
          Back to Inbox
        </Link>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Conversation</h1>
      </div>

      {loading ? (
        <p className="rounded-2xl border border-gray-200 bg-white px-4 py-6 text-sm text-gray-600">
          Loading messages...
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

      {!loading && !error ? (
        <div className="flex flex-1 flex-col gap-4">
          <div
            role="log"
            aria-label="Messages"
            aria-live="polite"
            className="flex flex-col gap-3 overflow-y-auto rounded-3xl border border-gray-200 bg-white p-4"
            style={{ minHeight: '24rem', maxHeight: '60vh' }}
          >
            {messages.length === 0 ? (
              <p className="text-center text-sm text-gray-500">No messages yet. Say hello!</p>
            ) : (
              messages.map((msg) => {
                const isMine = msg.sender_id === user?.id
                const seenByEntries = Array.from(seenBy.values()).filter(
                  (s) => s.lastMessageId === msg.id,
                )
                return (
                  <div key={msg.id} className="flex flex-col">
                    <div className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className={`max-w-xs rounded-2xl px-4 py-2 text-sm ${
                          isMine ? 'bg-indigo-500 text-white' : 'bg-gray-100 text-gray-900'
                        }`}
                      >
                        <p>{msg.content}</p>
                        <p
                          className={`mt-1 text-right text-xs ${isMine ? 'text-indigo-200' : 'text-gray-400'}`}
                        >
                          {formatTime(msg.sent_at)}
                          {isMine ? (msg.is_read ? ' · Read' : ' · Sent') : ''}
                        </p>
                      </div>
                    </div>
                    {seenByEntries.map((s) => (
                      <p
                        key={s.readerName}
                        aria-label={`Seen by ${s.readerName}`}
                        className={`text-xs text-gray-400 ${isMine ? 'text-right' : 'text-left'}`}
                      >
                        Seen by {s.readerName}
                      </p>
                    ))}
                  </div>
                )
              })
            )}
            <div ref={bottomRef} />
          </div>

          <div className="flex flex-col gap-2 rounded-3xl border border-gray-200 bg-white p-4 shadow-sm">
            {sendError ? (
              <p role="alert" className="text-xs text-red-600">
                {sendError}
              </p>
            ) : null}
            <div className="flex gap-3">
              <textarea
                aria-label="Message input"
                value={input}
                onChange={(e) => {
                  setInput(e.target.value)
                  setSendError(null)
                }}
                onKeyDown={handleKeyDown}
                placeholder="Type a message... (Enter to send)"
                rows={2}
                className="min-w-0 flex-1 resize-none rounded-2xl border border-gray-200 px-4 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />
              {reconnecting ? (
                <p role="status" className="self-center text-xs text-amber-600">
                  Reconnecting...
                </p>
              ) : null}
              <button
                type="button"
                onClick={sendMessage}
                disabled={!input.trim()}
                aria-label={connected ? 'Send message' : 'Send (connecting…)'}
                className="shrink-0 self-end rounded-full bg-indigo-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-600 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
