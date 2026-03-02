import { useEffect, useState } from 'react'
import NotificationList from '../components/NotificationList'
import apiClient from '../lib/apiClient'
import type { NotificationItem, NotificationsListResponse } from '../lib/notifications'

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [markingAllRead, setMarkingAllRead] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let isMounted = true

    apiClient
      .get<NotificationsListResponse>('/notifications', { params: { limit: 50 } })
      .then((response) => {
        if (!isMounted) {
          return
        }

        setNotifications(Array.isArray(response.data.items) ? response.data.items : [])
        setError(null)
      })
      .catch(() => {
        if (!isMounted) {
          return
        }

        setNotifications([])
        setError('Failed to load notifications.')
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

  const unreadCount = notifications.filter((notification) => notification.is_read === false).length

  async function handleMarkAllRead() {
    setMarkingAllRead(true)

    try {
      await apiClient.patch('/notifications/read-all')
      setNotifications((currentNotifications) =>
        currentNotifications.map((notification) => ({ ...notification, is_read: true })),
      )
    } catch {
      setError('Failed to update notifications.')
    } finally {
      setMarkingAllRead(false)
    }
  }

  return (
    <section className="mx-auto flex min-h-full w-full max-w-3xl flex-col gap-4 px-4 py-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Notifications</h1>
          <p className="text-sm text-gray-600">Recent activity across messages, matches, and packs.</p>
        </div>
        <button
          type="button"
          onClick={handleMarkAllRead}
          disabled={unreadCount === 0 || markingAllRead}
          className="rounded-full border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {markingAllRead ? 'Marking...' : 'Mark all as read'}
        </button>
      </div>

      {loading ? (
        <p className="rounded-2xl border border-gray-200 bg-white px-4 py-6 text-sm text-gray-600">
          Loading notifications...
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
        <NotificationList
          notifications={notifications}
          emptyTitle="No notifications yet."
          emptyDescription="New activity will show up here as you match, chat, and join packs."
        />
      ) : null}
    </section>
  )
}
