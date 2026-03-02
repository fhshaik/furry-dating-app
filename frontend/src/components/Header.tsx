import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import apiClient from '../lib/apiClient'
import NotificationList from './NotificationList'
import type { NotificationItem, NotificationsListResponse } from '../lib/notifications'

const NOTIFICATIONS_POLL_INTERVAL_MS = 30000

export default function Header() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const dropdownRef = useRef<HTMLDivElement | null>(null)
  const [unreadNotificationsCount, setUnreadNotificationsCount] = useState(0)
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false)
  const [loadingNotifications, setLoadingNotifications] = useState(false)
  const [notificationsError, setNotificationsError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) {
      setUnreadNotificationsCount(0)
      setNotifications([])
      setNotificationsError(null)
      setLoadingNotifications(false)
      return
    }

    let isMounted = true
    let intervalId: ReturnType<typeof setInterval> | null = null

    const loadNotifications = () => {
      setLoadingNotifications(true)

      void apiClient
        .get<NotificationsListResponse>('/notifications', { params: { limit: 100 } })
        .then((response) => {
          if (isMounted) {
            const items = Array.isArray(response.data.items) ? response.data.items : []
            const unreadCount = items.filter((notification) => notification.is_read === false).length
            setNotifications(items)
            setUnreadNotificationsCount(unreadCount)
            setNotificationsError(null)
          }
        })
        .catch(() => {
          if (isMounted) {
            setNotifications([])
            setUnreadNotificationsCount(0)
            setNotificationsError('Failed to load notifications.')
          }
        })
        .finally(() => {
          if (isMounted) {
            setLoadingNotifications(false)
          }
        })
    }

    loadNotifications()
    intervalId = setInterval(loadNotifications, NOTIFICATIONS_POLL_INTERVAL_MS)

    return () => {
      isMounted = false
      if (intervalId !== null) {
        clearInterval(intervalId)
      }
    }
  }, [location.pathname, user])

  useEffect(() => {
    setIsNotificationsOpen(false)
  }, [location.pathname])

  useEffect(() => {
    if (!isNotificationsOpen) {
      return
    }

    function handlePointerDown(event: MouseEvent) {
      if (!dropdownRef.current?.contains(event.target as Node)) {
        setIsNotificationsOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsNotificationsOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isNotificationsOpen])

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  function handleNotificationsClick() {
    setIsNotificationsOpen((currentValue) => !currentValue)
  }

  function handleViewAllNotifications() {
    setIsNotificationsOpen(false)
    navigate('/notifications')
  }

  return (
    <header className="fixed top-0 left-0 right-0 z-20 px-3 pt-3 sm:px-5">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between rounded-[2rem] border border-white/25 bg-[linear-gradient(135deg,rgba(255,248,235,0.94),rgba(250,222,191,0.86))] px-4 shadow-[0_18px_40px_rgba(42,19,28,0.18)] backdrop-blur-xl sm:px-5">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-[1.25rem] bg-[linear-gradient(135deg,#c55d35,#e8a15a)] text-2xl shadow-lg shadow-orange-900/20">
            🐾
          </div>
          <div>
            <span className="block font-['Copperplate','Georgia',serif] text-xl font-bold tracking-[0.14em] text-[#5b2a33] sm:text-2xl">
              FurConnect
            </span>
            <span className="block text-[10px] font-semibold uppercase tracking-[0.38em] text-[#9d654a]">
              Den mode
            </span>
          </div>
        </div>
      {user && (
        <div className="flex items-center gap-2">
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={handleNotificationsClick}
              aria-expanded={isNotificationsOpen}
              aria-haspopup="dialog"
              aria-label={
                unreadNotificationsCount > 0
                  ? `${unreadNotificationsCount} unread notifications`
                  : 'Notifications'
              }
              className="relative rounded-full border border-[#e6c39b] bg-white/65 p-2.5 text-[#7d3352] transition hover:border-[#d18b5d] hover:bg-white hover:text-[#5b2a33]"
            >
              <span aria-hidden="true" className="text-xl leading-none">
                🔔
              </span>
              {unreadNotificationsCount > 0 ? (
                <span className="absolute top-0 right-0 inline-flex min-h-5 min-w-5 -translate-y-1/4 translate-x-1/4 items-center justify-center rounded-full bg-[#b95839] px-1 text-[10px] font-semibold text-white shadow-md">
                  {unreadNotificationsCount > 99 ? '99+' : unreadNotificationsCount}
                </span>
              ) : null}
            </button>
            {isNotificationsOpen ? (
              <div
                role="dialog"
                aria-label="Recent notifications"
                className="absolute right-0 mt-3 w-[min(24rem,calc(100vw-2rem))] rounded-[2rem] border border-[#ebc99d] bg-[linear-gradient(180deg,#fffaf1,#f9e4c6)] p-3 shadow-[0_24px_50px_rgba(36,20,25,0.22)]"
              >
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-[#40202c]">Recent notifications</h2>
                    <p className="text-xs text-[#8a625c]">Fresh pings from your den.</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleViewAllNotifications}
                    className="rounded-full bg-[#7d3352] px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-[#5f2740]"
                  >
                    View all
                  </button>
                </div>

                {loadingNotifications ? (
                  <p className="rounded-[1.5rem] border border-[#edd4b4] bg-white/85 px-4 py-6 text-sm text-[#6e5252]">
                    Loading notifications...
                  </p>
                ) : null}

                {!loadingNotifications && notificationsError ? (
                  <p
                    role="alert"
                    className="rounded-[1.5rem] border border-red-200 bg-red-50 px-4 py-6 text-sm text-red-700"
                  >
                    {notificationsError}
                  </p>
                ) : null}

                {!loadingNotifications && !notificationsError ? (
                  <NotificationList
                    notifications={notifications.slice(0, 5)}
                    emptyTitle="No notifications yet."
                    emptyDescription="You are all caught up for now."
                    dense
                  />
                ) : null}
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-full border border-[#d6a677] bg-[#fff3e1] px-4 py-2 text-sm font-semibold text-[#6b3248] transition hover:bg-[#ffe5c5] hover:text-[#4f2334]"
          >
            Logout
          </button>
        </div>
      )}
      </div>
    </header>
  )
}
