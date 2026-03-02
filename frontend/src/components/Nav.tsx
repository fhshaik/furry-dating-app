import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Home', icon: '🏠' },
  { to: '/discover', label: 'Discover', icon: '🐾' },
  { to: '/matches', label: 'Matches', icon: '💞' },
  { to: '/inbox', label: 'Inbox', icon: '💬' },
  { to: '/my-packs', label: 'Packs', icon: '🐺' },
  { to: '/profile', label: 'Profile', icon: '🦊' },
]

interface NavProps {
  unreadCount?: number
}

export default function Nav({ unreadCount = 0 }: NavProps) {
  return (
    <nav
      aria-label="Main navigation"
      className="fixed right-0 bottom-0 left-0 z-20 px-3 pb-3 sm:px-5"
    >
      <div className="mx-auto flex h-18 w-full max-w-5xl items-center justify-around rounded-[2rem] border border-white/20 bg-[linear-gradient(180deg,rgba(59,27,39,0.88),rgba(41,18,30,0.96))] px-2 text-[#f9e3c5] shadow-[0_26px_60px_rgba(19,8,15,0.38)] backdrop-blur-xl">
        {links.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex min-w-0 flex-col items-center gap-1 rounded-[1.25rem] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                isActive
                  ? 'bg-[linear-gradient(135deg,#f2b467,#d87c45)] text-[#3c1f29] shadow-lg shadow-orange-950/20'
                  : 'text-[#f3d9bc] hover:bg-white/8'
              }`
            }
            aria-label={label}
          >
            <span className="relative text-2xl leading-none">
              {icon}
              {to === '/inbox' && unreadCount > 0 ? (
                <span
                  aria-label={`${unreadCount} unread messages`}
                  className="absolute -top-1 -right-3 inline-flex min-h-5 min-w-5 items-center justify-center rounded-full bg-[#ffcf7d] px-1 text-[10px] font-bold text-[#5d2434]"
                >
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              ) : null}
            </span>
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
