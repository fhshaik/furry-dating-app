import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import apiClient from '../lib/apiClient'

const RELATIONSHIP_STYLES = ['monogamous', 'polyamorous', 'open', 'casual', 'unsure']

export default function ProfileEditPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [displayName, setDisplayName] = useState(user?.display_name ?? '')
  const [bio, setBio] = useState(user?.bio ?? '')
  const [age, setAge] = useState(user?.age?.toString() ?? '')
  const [city, setCity] = useState(user?.city ?? '')
  const [relationshipStyle, setRelationshipStyle] = useState(user?.relationship_style ?? '')
  const [nsfwEnabled, setNsfwEnabled] = useState(user?.nsfw_enabled ?? false)

  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const [showAgeModal, setShowAgeModal] = useState(false)
  const [modalAge, setModalAge] = useState('')
  const [modalError, setModalError] = useState<string | null>(null)

  function handleNsfwToggle(checked: boolean) {
    if (!checked) {
      setNsfwEnabled(false)
      return
    }
    const parsedAge = age ? parseInt(age, 10) : null
    if (parsedAge !== null && parsedAge >= 18) {
      setNsfwEnabled(true)
    } else {
      setModalAge(age)
      setModalError(null)
      setShowAgeModal(true)
    }
  }

  function handleModalConfirm() {
    const parsed = parseInt(modalAge, 10)
    if (!modalAge || isNaN(parsed) || parsed < 18) {
      setModalError('You must be 18 or older to enable NSFW content.')
      return
    }
    setAge(modalAge)
    setNsfwEnabled(true)
    setShowAgeModal(false)
    setModalAge('')
    setModalError(null)
  }

  function handleModalCancel() {
    setShowAgeModal(false)
    setModalAge('')
    setModalError(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(false)
    setSubmitting(true)

    const payload: Record<string, string | number | boolean | null> = {
      display_name: displayName,
      bio: bio || null,
      age: age ? parseInt(age, 10) : null,
      city: city || null,
      relationship_style: relationshipStyle || null,
      nsfw_enabled: nsfwEnabled,
    }

    try {
      await apiClient.patch('/users/me', payload)
      setSuccess(true)
    } catch {
      setError('Failed to save profile. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="mx-auto w-full max-w-2xl px-4 py-8 sm:py-10">
      <div className="overflow-hidden rounded-[2.5rem] border border-[#f0c796] bg-[linear-gradient(145deg,rgba(255,247,236,0.96),rgba(249,227,200,0.9))] p-6 shadow-[0_24px_60px_rgba(33,14,23,0.22)] sm:p-8">
        <div className="mb-8">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-[#aa6649]">
            Profile settings
          </p>
          <h1 className="mt-3 font-['Copperplate','Georgia',serif] text-4xl font-bold text-[#45212e]">
            Edit Profile
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-7 text-[#6b5152]">
            Tune the parts other furs see first: your name, bio, city, relationship style, and
            content preferences.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <div>
          <label className="mb-1 block text-sm font-semibold text-[#5f3b45]" htmlFor="display_name">
            Display Name
          </label>
          <input
            id="display_name"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            className="w-full rounded-[1.2rem] border border-[#d8b089] bg-white/75 px-4 py-3 text-base text-[#241419] outline-none transition focus:border-[#b95839] focus:ring-2 focus:ring-[#e9b26b]/60"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-semibold text-[#5f3b45]" htmlFor="bio">
            Bio
          </label>
          <textarea
            id="bio"
            rows={3}
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            className="w-full rounded-[1.2rem] border border-[#d8b089] bg-white/75 px-4 py-3 text-base text-[#241419] outline-none transition focus:border-[#b95839] focus:ring-2 focus:ring-[#e9b26b]/60"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-semibold text-[#5f3b45]" htmlFor="age">
            Age
          </label>
          <input
            id="age"
            type="number"
            min={13}
            max={120}
            value={age}
            onChange={(e) => setAge(e.target.value)}
            className="w-full rounded-[1.2rem] border border-[#d8b089] bg-white/75 px-4 py-3 text-base text-[#241419] outline-none transition focus:border-[#b95839] focus:ring-2 focus:ring-[#e9b26b]/60"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-semibold text-[#5f3b45]" htmlFor="city">
            City
          </label>
          <input
            id="city"
            type="text"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="w-full rounded-[1.2rem] border border-[#d8b089] bg-white/75 px-4 py-3 text-base text-[#241419] outline-none transition focus:border-[#b95839] focus:ring-2 focus:ring-[#e9b26b]/60"
          />
        </div>

        <div>
          <label
            className="mb-1 block text-sm font-semibold text-[#5f3b45]"
            htmlFor="relationship_style"
          >
            Relationship Style
          </label>
          <select
            id="relationship_style"
            value={relationshipStyle}
            onChange={(e) => setRelationshipStyle(e.target.value)}
            className="w-full rounded-[1.2rem] border border-[#d8b089] bg-white/75 px-4 py-3 text-base text-[#241419] outline-none transition focus:border-[#b95839] focus:ring-2 focus:ring-[#e9b26b]/60"
          >
            <option value="">— select —</option>
            {RELATIONSHIP_STYLES.map((style) => (
              <option key={style} value={style}>
                {style.charAt(0).toUpperCase() + style.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-start gap-3 rounded-[1.4rem] border border-[#e4bf96] bg-white/45 px-4 py-4">
          <input
            id="nsfw_enabled"
            type="checkbox"
            checked={nsfwEnabled}
            onChange={(e) => handleNsfwToggle(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-[#b98a66] text-[#7d3352] focus:ring-[#b95839]"
          />
          <label htmlFor="nsfw_enabled" className="text-sm font-medium leading-6 text-[#5f3b45]">
            Enable NSFW content (18+)
          </label>
        </div>

        {error && <p className="text-sm font-medium text-red-700">{error}</p>}
        {success && <p className="text-sm font-medium text-green-700">Profile saved successfully.</p>}

        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={submitting}
            className="rounded-full bg-[#7d3352] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#5f2740] disabled:opacity-50"
          >
            {submitting ? 'Saving...' : 'Save'}
          </button>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="text-sm font-medium text-[#7a5f5d] transition hover:text-[#4f2334]"
          >
            Cancel
          </button>
        </div>
        </form>
      </div>

      {showAgeModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="age-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
        >
          <div className="w-full max-w-sm rounded-[2rem] border border-[#f0c796] bg-[linear-gradient(180deg,#fff7ea,#f8e0bf)] p-6 shadow-[0_24px_60px_rgba(18,8,13,0.34)]">
            <h2 id="age-modal-title" className="mb-2 text-lg font-semibold text-[#45212e]">
              Age Confirmation Required
            </h2>
            <p className="mb-4 text-sm leading-6 text-[#6b5152]">
              NSFW content is only available to users who are 18 or older. Please confirm your age
              to continue.
            </p>
            <label className="mb-1 block text-sm font-medium text-[#5f3b45]" htmlFor="modal_age">
              Your Age
            </label>
            <input
              id="modal_age"
              type="number"
              min={18}
              max={120}
              value={modalAge}
              onChange={(e) => setModalAge(e.target.value)}
              className="mb-3 w-full rounded-[1.2rem] border border-[#d8b089] bg-white/80 px-4 py-3 text-base text-[#241419] outline-none transition focus:border-[#b95839] focus:ring-2 focus:ring-[#e9b26b]/60"
            />
            {modalError && <p className="mb-3 text-sm font-medium text-red-700">{modalError}</p>}
            <div className="flex gap-3">
              <button
                type="button"
                onClick={handleModalConfirm}
                className="flex-1 rounded-full bg-[#7d3352] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#5f2740]"
              >
                Confirm
              </button>
              <button
                type="button"
                onClick={handleModalCancel}
                className="flex-1 rounded-full border border-[#d8b089] bg-white/70 px-4 py-2.5 text-sm font-semibold text-[#5f3b45] transition hover:bg-white"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
