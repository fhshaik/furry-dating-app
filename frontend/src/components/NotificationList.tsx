import { Link } from 'react-router-dom'
import {
  formatNotificationDate,
  getNotificationHref,
  getNotificationDescription,
  getNotificationTitle,
  type NotificationItem,
} from '../lib/notifications'

interface NotificationListProps {
  notifications: NotificationItem[]
  emptyTitle: string
  emptyDescription: string
  dense?: boolean
}

export default function NotificationList({
  notifications,
  emptyTitle,
  emptyDescription,
  dense = false,
}: NotificationListProps) {
  function renderNotificationContent(notification: NotificationItem) {
    return (
      <>
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              {!notification.is_read ? (
                <span
                  aria-label="Unread notification"
                  className="inline-flex h-2.5 w-2.5 rounded-full bg-indigo-500"
                />
              ) : null}
              <h2 className="text-sm font-semibold text-gray-900">
                {getNotificationTitle(notification.type)}
              </h2>
            </div>
            <p className="text-sm text-gray-600">
              {getNotificationDescription(notification.type, notification.payload)}
            </p>
          </div>
          <time
            dateTime={notification.created_at}
            className="shrink-0 text-xs font-medium text-gray-500"
          >
            {formatNotificationDate(notification.created_at)}
          </time>
        </div>
      </>
    )
  }

  if (notifications.length === 0) {
    return (
      <div
        className={`rounded-3xl border border-dashed border-gray-300 bg-white text-center ${
          dense ? 'px-4 py-6' : 'px-6 py-10'
        }`}
      >
        <h2 className="text-lg font-semibold text-gray-900">{emptyTitle}</h2>
        <p className="mt-2 text-sm text-gray-600">{emptyDescription}</p>
      </div>
    )
  }

  return (
    <ul className={dense ? 'space-y-2' : 'space-y-3'} aria-label="Notifications">
      {notifications.map((notification) => {
        const href = getNotificationHref(notification)

        return (
          <li key={notification.id}>
            {href ? (
              <Link
                to={href}
                className={`block rounded-3xl border bg-white shadow-sm transition hover:border-indigo-200 hover:bg-indigo-50 ${
                  notification.is_read
                    ? 'border-gray-200'
                    : 'border-indigo-200 bg-indigo-50/50 ring-1 ring-indigo-100'
                } ${dense ? 'p-3' : 'p-4'}`}
              >
                {renderNotificationContent(notification)}
              </Link>
            ) : (
              <article
                className={`rounded-3xl border bg-white shadow-sm ${
                  notification.is_read
                    ? 'border-gray-200'
                    : 'border-indigo-200 bg-indigo-50/50 ring-1 ring-indigo-100'
                } ${dense ? 'p-3' : 'p-4'}`}
              >
                {renderNotificationContent(notification)}
              </article>
            )}
          </li>
        )
      })}
    </ul>
  )
}
