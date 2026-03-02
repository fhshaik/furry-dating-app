export default function LoginPage() {
  return (
    <section className="flex min-h-full items-center py-6 sm:py-10">
      <div className="mx-auto grid w-full max-w-6xl gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(22rem,0.9fr)]">
        <div className="relative overflow-hidden rounded-[2.75rem] border border-[#f4cea4] bg-[linear-gradient(150deg,rgba(255,248,237,0.96),rgba(249,223,188,0.84))] p-8 shadow-[0_28px_70px_rgba(34,16,24,0.22)] sm:p-10">
          <div
            aria-hidden="true"
            className="absolute top-0 right-0 h-56 w-56 translate-x-10 -translate-y-10 rounded-full bg-[#f1a462]/35 blur-3xl"
          />
          <div className="relative">
            <p className="text-xs font-semibold uppercase tracking-[0.42em] text-[#aa6649]">
              Find your pack
            </p>
            <h1 className="mt-4 font-['Copperplate','Georgia',serif] text-5xl font-bold leading-tight text-[#45212e] sm:text-6xl">
              FurConnect
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-[#674b4d]">
              A dating and community den for furries. Meet through fursona-first profiles, shared
              species vibes, soft late-night chat energy, and packs that actually feel lived in.
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-3">
              <div className="rounded-[1.8rem] border border-[#efc692] bg-white/65 p-4">
                <p className="text-2xl">🦊</p>
                <p className="mt-2 text-sm font-semibold uppercase tracking-[0.18em] text-[#8c4e4d]">
                  Fursonas first
                </p>
              </div>
              <div className="rounded-[1.8rem] border border-[#efc692] bg-white/65 p-4">
                <p className="text-2xl">🐺</p>
                <p className="mt-2 text-sm font-semibold uppercase tracking-[0.18em] text-[#8c4e4d]">
                  Pack culture
                </p>
              </div>
              <div className="rounded-[1.8rem] border border-[#efc692] bg-white/65 p-4">
                <p className="text-2xl">✨</p>
                <p className="mt-2 text-sm font-semibold uppercase tracking-[0.18em] text-[#8c4e4d]">
                  Warm aesthetic
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-[2.75rem] border border-white/15 bg-[linear-gradient(180deg,rgba(69,34,46,0.94),rgba(34,16,24,0.98))] p-8 text-[#fae8d1] shadow-[0_28px_70px_rgba(18,8,13,0.4)]">
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[#f0bd80]">
            Enter the den
          </p>
          <h2 className="mt-3 font-['Copperplate','Georgia',serif] text-3xl font-bold text-white">
            Sign in and start roaming.
          </h2>
          <p className="mt-3 text-sm leading-7 text-[#eedbcb]">
            Pick your portal, load your profile, and drop into a warmer furry community experience.
          </p>

          <div className="mt-8 flex flex-col gap-4">
            <a
              href="/api/auth/google"
              className="flex items-center justify-center gap-3 rounded-[1.4rem] border border-[#f1d5b2] bg-[#fff8ee] px-6 py-4 text-sm font-semibold text-[#5e3040] shadow-sm transition hover:bg-white"
            >
          <svg className="h-5 w-5" viewBox="0 0 24 24" aria-hidden="true">
            <path
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              fill="#4285F4"
            />
            <path
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              fill="#34A853"
            />
            <path
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"
              fill="#FBBC05"
            />
            <path
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              fill="#EA4335"
            />
          </svg>
          Sign in with Google
            </a>

            <a
              href="/api/auth/discord"
              className="flex items-center justify-center gap-3 rounded-[1.4rem] bg-[linear-gradient(135deg,#8d4361,#5d2943)] px-6 py-4 text-sm font-semibold text-white shadow-sm transition hover:brightness-110"
            >
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M20.317 4.492c-1.53-.69-3.17-1.2-4.885-1.49a.075.075 0 0 0-.079.036c-.21.369-.444.85-.608 1.23a18.566 18.566 0 0 0-5.487 0 12.36 12.36 0 0 0-.617-1.23A.077.077 0 0 0 8.562 3c-1.714.29-3.354.8-4.885 1.491a.07.07 0 0 0-.032.027C.533 9.093-.32 13.555.099 17.961a.08.08 0 0 0 .031.055 20.03 20.03 0 0 0 5.993 2.98.078.078 0 0 0 .084-.026 13.83 13.83 0 0 0 1.226-1.963.074.074 0 0 0-.041-.104 13.201 13.201 0 0 1-1.872-.878.075.075 0 0 1-.008-.125c.126-.093.252-.19.372-.287a.075.075 0 0 1 .078-.01c3.927 1.764 8.18 1.764 12.061 0a.075.075 0 0 1 .079.009c.12.098.245.195.372.288a.075.075 0 0 1-.006.125c-.598.344-1.22.635-1.873.877a.075.075 0 0 0-.041.105c.36.687.772 1.341 1.225 1.962a.077.077 0 0 0 .084.028 19.963 19.963 0 0 0 6.002-2.981.076.076 0 0 0 .032-.054c.5-5.094-.838-9.52-3.549-13.442a.06.06 0 0 0-.031-.028zM8.02 15.278c-1.182 0-2.157-1.069-2.157-2.38 0-1.312.956-2.38 2.157-2.38 1.21 0 2.176 1.077 2.157 2.38 0 1.312-.956 2.38-2.157 2.38zm7.975 0c-1.183 0-2.157-1.069-2.157-2.38 0-1.312.955-2.38 2.157-2.38 1.21 0 2.176 1.077 2.157 2.38 0 1.312-.946 2.38-2.157 2.38z" />
          </svg>
          Sign in with Discord
            </a>

            <a
              href="/api/auth/demo"
              className="mt-2 text-center text-sm font-medium text-[#f0c58d] underline decoration-[#f0c58d]/50 underline-offset-4 transition hover:text-[#ffe7c2]"
            >
              Try demo (example data)
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}
