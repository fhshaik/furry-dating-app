import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import apiClient from '../lib/apiClient'
import Header from './Header'
import Nav from './Nav'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const { user } = useAuth()
  const location = useLocation()
  const [unreadCount, setUnreadCount] = useState(0)

  useEffect(() => {
    if (!user) {
      setUnreadCount(0)
      return
    }

    let isMounted = true

    apiClient
      .get<Array<{ unread_count?: number }>>('/conversations')
      .then((response) => {
        if (!isMounted) {
          return
        }

        const totalUnread = response.data.reduce(
          (total, conversation) => total + (conversation.unread_count ?? 0),
          0,
        )
        setUnreadCount(totalUnread)
      })
      .catch(() => {
        if (isMounted) {
          setUnreadCount(0)
        }
      })

    return () => {
      isMounted = false
    }
  }, [location.pathname, user])

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden text-stone-950">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-x-0 top-[-10rem] h-[42rem] bg-[radial-gradient(circle_at_top,rgba(255,239,210,0.72),rgba(245,198,153,0.28)_38%,rgba(125,51,82,0.08)_62%,transparent_80%)] blur-2xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-20 left-[-8rem] h-72 w-72 rounded-full bg-orange-200/25 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute right-[-7rem] top-40 h-80 w-80 rounded-full bg-rose-300/15 blur-3xl"
      />
      <Header />
      <main className="relative flex min-h-0 flex-1 flex-col overflow-x-hidden overflow-y-auto px-3 pt-20 pb-24 sm:px-5">
        <div className="mx-auto flex min-h-full w-full max-w-6xl flex-1 flex-col">
          {children}
        </div>
      </main>
      <Nav unreadCount={unreadCount} />
    </div>
  )
}
