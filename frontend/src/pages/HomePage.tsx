import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function HomePage() {
  const { user } = useAuth()
  const displayName = user?.display_name ?? 'there'
  const quickLinks = [
    {
      to: '/discover',
      label: 'Discover',
      description: 'Scout new profiles, spot shared vibes, and swipe from the den floor.',
      icon: '🐾',
      accent: 'from-[#f6cf99] via-[#ed9c62] to-[#c35a3e]',
    },
    {
      to: '/matches',
      label: 'Matches',
      description: 'Check your sparks, mutual crushes, and fresh chemistry.',
      icon: '💞',
      accent: 'from-[#f5b7b1] via-[#d77f86] to-[#8a435f]',
    },
    {
      to: '/inbox',
      label: 'Inbox',
      description: 'Keep late-night chats, pack banter, and meetup plans moving.',
      icon: '💬',
      accent: 'from-[#f0d3a4] via-[#d59269] to-[#8f4b4c]',
    },
    {
      to: '/my-packs',
      label: 'My Packs',
      description: 'See your circles, group chat dens, and recruitment status.',
      icon: '🐺',
      accent: 'from-[#ead2ad] via-[#c77b56] to-[#6b3248]',
    },
  ]

  return (
    <section className="flex min-h-full w-full flex-col gap-8 py-4 sm:py-8">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_minmax(21rem,0.8fr)]">
        <div className="relative overflow-hidden rounded-[2.5rem] border border-[#f2cfaa] bg-[linear-gradient(145deg,rgba(255,247,234,0.96),rgba(249,223,187,0.86))] p-8 shadow-[0_28px_70px_rgba(34,16,24,0.22)] sm:p-10">
          <div
            aria-hidden="true"
            className="absolute top-0 right-0 h-52 w-52 translate-x-10 -translate-y-10 rounded-full bg-[#f0aa63]/35 blur-3xl"
          />
          <div
            aria-hidden="true"
            className="absolute bottom-0 left-0 h-48 w-48 -translate-x-8 translate-y-8 rounded-full bg-[#9e4e50]/15 blur-3xl"
          />
          <p className="text-xs font-semibold uppercase tracking-[0.42em] text-[#a26148]">
            Welcome to FurConnect
          </p>
          <h1 className="mt-5 font-['Copperplate','Georgia',serif] text-4xl leading-tight font-bold text-[#45212e] sm:text-5xl">
            Hey {displayName}, your den is live.
          </h1>
          <p className="mt-4 max-w-2xl text-lg leading-8 text-[#684c4c]">
            Built for furs who want warmth, chemistry, and community. Browse lush profiles, find
            your next pack, and keep every conversation inside one cozy shared lodge.
          </p>
          <div className="mt-8 flex flex-wrap gap-3 text-sm font-semibold">
            <span className="rounded-full border border-[#efc38f] bg-white/70 px-4 py-2 text-[#7d3352]">
              Convention energy
            </span>
            <span className="rounded-full border border-[#efc38f] bg-white/70 px-4 py-2 text-[#7d3352]">
              Pack-first design
            </span>
            <span className="rounded-full border border-[#efc38f] bg-white/70 px-4 py-2 text-[#7d3352]">
              Fursona-forward profiles
            </span>
          </div>
        </div>

        <aside className="rounded-[2.5rem] border border-[#f0c796] bg-[linear-gradient(180deg,rgba(74,36,48,0.92),rgba(45,21,31,0.98))] p-7 text-[#f9e6ce] shadow-[0_24px_60px_rgba(26,10,17,0.36)]">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-[#f1b774]">
            Tonight’s vibe
          </p>
          <h2 className="mt-3 font-['Copperplate','Georgia',serif] text-3xl font-bold text-white">
            Soft lodge, bright sparks.
          </h2>
          <p className="mt-4 text-sm leading-7 text-[#efdbcb]">
            Keep things playful, affectionate, and unmistakably furry. This build now leans into
            warm fur tones, den-club lighting, and pack symbolism instead of default social-app UI.
          </p>
          <div className="mt-6 space-y-4">
            <div className="rounded-[1.75rem] border border-white/10 bg-white/6 p-4">
              <p className="text-xs uppercase tracking-[0.28em] text-[#f0be86]">Profile focus</p>
              <p className="mt-2 text-sm text-[#fff1df]">Fursona names, species, and traits stay visually dominant.</p>
            </div>
            <div className="rounded-[1.75rem] border border-white/10 bg-white/6 p-4">
              <p className="text-xs uppercase tracking-[0.28em] text-[#f0be86]">Community focus</p>
              <p className="mt-2 text-sm text-[#fff1df]">Packs, dens, and event-night energy are treated as first-class.</p>
            </div>
          </div>
        </aside>
      </div>

      <div className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-[0.28em] text-[#f8dfc3]">
          Quick links
        </h2>
        <ul className="grid gap-4 lg:grid-cols-2" aria-label="Quick navigation">
          {quickLinks.map(({ to, label, description, icon, accent }) => (
            <li key={to}>
              <Link
                to={to}
                className="group relative flex items-center gap-4 overflow-hidden rounded-[2rem] border border-[#f0c796] bg-[linear-gradient(145deg,rgba(255,247,236,0.96),rgba(250,228,198,0.88))] p-5 shadow-[0_18px_40px_rgba(38,17,27,0.18)] transition hover:-translate-y-1 hover:shadow-[0_26px_60px_rgba(38,17,27,0.24)]"
              >
                <div className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-[1.35rem] bg-linear-to-br ${accent} text-2xl shadow-lg shadow-orange-950/20`}>
                  {icon}
                </div>
                <div className="min-w-0">
                  <span className="font-['Copperplate','Georgia',serif] text-xl font-bold text-[#45212e]">
                    {label}
                  </span>
                  <p className="mt-1 text-sm leading-6 text-[#6a4e4e]">{description}</p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
