import { useEffect, useRef, useState, type TouchEvent } from 'react'
import { Link } from 'react-router-dom'
import apiClient from '../lib/apiClient'
import { useAuth } from '../contexts/AuthContext'
import SwipeCard, { type SwipeCardCandidate } from '../components/SwipeCard'

interface SpeciesOption {
  id: number
  name: string
  slug: string
}

type DiscoverCandidate = SwipeCardCandidate & {
  created_at: string
}

interface DiscoverResponse {
  items: DiscoverCandidate[]
  page: number
  limit: number
  total: number
  has_more: boolean
}

type PackDiscoverCandidate = Extract<SwipeCardCandidate, { type: 'pack' }> & {
  type: 'pack'
  created_at: string
}

interface PackDiscoverResponse {
  items: PackDiscoverCandidate[]
  page: number
  limit: number
  total: number
  has_more: boolean
}

interface SwipeResponse {
  id: number
  swiper_id: number
  target_user_id: number | null
  target_pack_id: number | null
  action: 'like' | 'pass'
  created_at: string
  is_match: boolean
}

const relationshipOptions = [
  { value: '', label: 'Any relationship style' },
  { value: 'monogamous', label: 'Monogamous' },
  { value: 'polyamorous', label: 'Polyamorous' },
  { value: 'open', label: 'Open' },
  { value: 'casual', label: 'Casual' },
  { value: 'unsure', label: 'Unsure' },
]

const SWIPE_THRESHOLD_PX = 110
const SWIPE_EXIT_OFFSET_PX = 420
const SWIPE_EXIT_DURATION_MS = 300
const MIN_AGE_LIMIT = 18
const MAX_AGE_LIMIT = 99
const SWIPE_TIPS_STORAGE_KEY = 'discover-swipe-tips-seen'

function HeartIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M11.645 20.91l-.007-.003-.022-.012a15.247 15.247 0 01-.383-.218 25.18 25.18 0 01-4.244-3.17C4.688 15.36 2.25 12.174 2.25 8.25 2.25 5.322 4.714 3 7.688 3A5.5 5.5 0 0112 5.052 5.5 5.5 0 0116.313 3c2.973 0 5.437 2.322 5.437 5.25 0 3.925-2.438 7.111-4.739 9.256a25.175 25.175 0 01-4.244 3.17 15.247 15.247 0 01-.383.219l-.022.012-.007.004-.003.001a.752.752 0 01-.704 0l-.003-.001z" />
    </svg>
  )
}

interface SwipeExitState {
  action: 'like' | 'pass'
  candidateId: number
}

interface MatchOverlayState {
  candidateName: string
}

type DiscoverTab = 'profiles' | 'packs'

function isPackCandidate(candidate: DiscoverCandidate): candidate is DiscoverCandidate & { type: 'pack' } {
  return candidate.type === 'pack'
}

function getCandidateName(candidate: DiscoverCandidate) {
  return isPackCandidate(candidate) ? candidate.name : candidate.display_name
}

interface DiscoverPageProps {
  initialTab?: DiscoverTab
}

export default function DiscoverPage({ initialTab = 'profiles' }: DiscoverPageProps) {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState<DiscoverTab>(initialTab)
  const [speciesOptions, setSpeciesOptions] = useState<SpeciesOption[]>([])
  const [candidates, setCandidates] = useState<DiscoverCandidate[]>([])
  const [selectedSpecies, setSelectedSpecies] = useState<string[]>([])
  const [city, setCity] = useState('')
  const [packSearch, setPackSearch] = useState('')
  const [minAge, setMinAge] = useState(MIN_AGE_LIMIT)
  const [maxAge, setMaxAge] = useState(MAX_AGE_LIMIT)
  const [relationshipStyle, setRelationshipStyle] = useState('')
  const [includeNsfw, setIncludeNsfw] = useState(user?.nsfw_enabled ?? false)
  const [isFilterDrawerOpen, setIsFilterDrawerOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [swipeError, setSwipeError] = useState<string | null>(null)
  const [matchOverlay, setMatchOverlay] = useState<MatchOverlayState | null>(null)
  const [isSubmittingSwipe, setIsSubmittingSwipe] = useState(false)
  const [dragOffsetX, setDragOffsetX] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [exitSwipe, setExitSwipe] = useState<SwipeExitState | null>(null)
  const [swipeTipsCollapsed, setSwipeTipsCollapsed] = useState(
    () => typeof sessionStorage !== 'undefined' && sessionStorage.getItem(SWIPE_TIPS_STORAGE_KEY) === '1',
  )
  const swipeStartXRef = useRef<number | null>(null)
  const dragOffsetRef = useRef(0)
  const swipeExitTimeoutRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      clearSwipeExitTimeout()
    }
  }, [])

  useEffect(() => {
    try {
      sessionStorage.setItem(SWIPE_TIPS_STORAGE_KEY, '1')
    } catch {
      // ignore
    }
  }, [])

  function clearSwipeExitTimeout() {
    if (swipeExitTimeoutRef.current !== null) {
      window.clearTimeout(swipeExitTimeoutRef.current)
      swipeExitTimeoutRef.current = null
    }
  }

  useEffect(() => {
    apiClient
      .get<SpeciesOption[]>('/species')
      .then((res) => setSpeciesOptions(res.data))
      .catch(() => setSpeciesOptions([]))
  }, [])

  useEffect(() => {
    setIncludeNsfw(user?.nsfw_enabled ?? false)
  }, [user?.nsfw_enabled])

  useEffect(() => {
    void loadCandidates(activeTab, {
      species: selectedSpecies,
      city,
      minAge,
      maxAge,
      relationshipStyle,
      includeNsfw: user?.nsfw_enabled ? includeNsfw : false,
      packSearch,
    })
    // Initial load and tab switches should reflect the current form values.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  async function loadCandidates(
    tab: DiscoverTab,
    filters: {
    species: string[]
    city: string
    minAge: number
    maxAge: number
    relationshipStyle: string
    includeNsfw: boolean
    packSearch: string
  },
  ) {
    clearSwipeExitTimeout()
    setExitSwipe(null)
    resetDragState()
    setLoading(true)
    setError(null)
    setSwipeError(null)
    setMatchOverlay(null)

    try {
      if (tab === 'packs') {
        const res = await apiClient.get<PackDiscoverResponse>('/packs', {
          params: {
            species: filters.species.length > 0 ? filters.species.join(',') : undefined,
            search: filters.packSearch.trim() || undefined,
          },
        })
        setCandidates(res.data.items.map((item) => ({ ...item, type: 'pack' })))
      } else {
        const res = await apiClient.get<DiscoverResponse>('/discover', {
          params: {
            species: filters.species.length > 0 ? filters.species.join(',') : undefined,
            city: filters.city || undefined,
            min_age: filters.minAge > MIN_AGE_LIMIT ? filters.minAge : undefined,
            max_age: filters.maxAge < MAX_AGE_LIMIT ? filters.maxAge : undefined,
            relationship_style: filters.relationshipStyle || undefined,
            include_nsfw: filters.includeNsfw,
          },
        })
        setCandidates(res.data.items)
      }
    } catch {
      setError(tab === 'packs' ? 'Failed to load pack results.' : 'Failed to load discover results.')
      setCandidates([])
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await loadCandidates(activeTab, {
      species: selectedSpecies,
      city,
      minAge,
      maxAge,
      relationshipStyle,
      includeNsfw: user?.nsfw_enabled ? includeNsfw : false,
      packSearch,
    })
    setIsFilterDrawerOpen(false)
  }

  function handleReset() {
    setSelectedSpecies([])
    setCity('')
    setPackSearch('')
    setMinAge(MIN_AGE_LIMIT)
    setMaxAge(MAX_AGE_LIMIT)
    setRelationshipStyle('')
    const nextIncludeNsfw = user?.nsfw_enabled ?? false
    setIncludeNsfw(nextIncludeNsfw)
    setIsFilterDrawerOpen(false)
    void loadCandidates(activeTab, {
      species: [],
      city: '',
      minAge: MIN_AGE_LIMIT,
      maxAge: MAX_AGE_LIMIT,
      relationshipStyle: '',
      includeNsfw: nextIncludeNsfw,
      packSearch: '',
    })
  }

  function toggleSpecies(name: string) {
    setSelectedSpecies((current) =>
      current.includes(name) ? current.filter((value) => value !== name) : [...current, name],
    )
  }

  function handleMinAgeChange(nextValue: number) {
    setMinAge(Math.min(nextValue, maxAge))
  }

  function handleMaxAgeChange(nextValue: number) {
    setMaxAge(Math.max(nextValue, minAge))
  }

  async function handleSwipe(action: 'like' | 'pass') {
    const currentCandidate = candidates[0]
    if (!currentCandidate || isSubmittingSwipe || exitSwipe) {
      return
    }

    setIsSubmittingSwipe(true)
    setSwipeError(null)

    try {
      const payload = isPackCandidate(currentCandidate)
        ? {
            action,
            target_pack_id: currentCandidate.id,
          }
        : {
            action,
            target_user_id: currentCandidate.id,
          }
      const res = await apiClient.post<SwipeResponse>('/swipes', payload)

      setExitSwipe({
        action,
        candidateId: currentCandidate.id,
      })
      setMatchOverlay(
        res.data.is_match
          ? {
              candidateName: getCandidateName(currentCandidate),
            }
          : null,
      )

      swipeExitTimeoutRef.current = window.setTimeout(() => {
        setCandidates((previous) => previous.filter((candidate) => candidate.id !== currentCandidate.id))
        setExitSwipe((previous) =>
          previous?.candidateId === currentCandidate.id ? null : previous,
        )
        setIsSubmittingSwipe(false)
        resetDragState()
        swipeExitTimeoutRef.current = null
      }, SWIPE_EXIT_DURATION_MS)
    } catch {
      setSwipeError(`Failed to ${action === 'like' ? 'like' : 'pass'} this profile.`)
      resetDragState()
      setExitSwipe(null)
      setIsSubmittingSwipe(false)
    }
  }

  function resetDragState() {
    swipeStartXRef.current = null
    dragOffsetRef.current = 0
    setDragOffsetX(0)
    setIsDragging(false)
  }

  function handleCardTouchStart(event: TouchEvent<HTMLElement>) {
    if (!activeCandidate || isSubmittingSwipe || exitSwipe) {
      return
    }

    swipeStartXRef.current = event.touches[0]?.clientX ?? null
    setIsDragging(true)
    dragOffsetRef.current = 0
    setDragOffsetX(0)
  }

  function handleCardTouchMove(event: TouchEvent<HTMLElement>) {
    const startX = swipeStartXRef.current
    const currentX = event.touches[0]?.clientX
    if (startX === null || currentX === undefined) {
      return
    }

    const nextOffset = currentX - startX
    dragOffsetRef.current = nextOffset
    setDragOffsetX(nextOffset)
  }

  function handleCardTouchEnd() {
    const finalOffset = dragOffsetRef.current
    swipeStartXRef.current = null
    setIsDragging(false)

    if (Math.abs(finalOffset) < SWIPE_THRESHOLD_PX) {
      resetDragState()
      return
    }

    void handleSwipe(finalOffset > 0 ? 'like' : 'pass')
  }

  function handleTabChange(nextTab: DiscoverTab) {
    if (nextTab === activeTab) {
      return
    }

    setIsFilterDrawerOpen(false)
    setSwipeError(null)
    setMatchOverlay(null)
    setActiveTab(nextTab)
  }

  const activeCandidate = candidates[0]
  const stackedCandidates = candidates.slice(0, 3)
  const activeFilterCount =
    activeTab === 'packs'
      ? selectedSpecies.length + (packSearch.trim() ? 1 : 0)
      : selectedSpecies.length +
        (city.trim() ? 1 : 0) +
        (relationshipStyle ? 1 : 0) +
        (minAge > MIN_AGE_LIMIT || maxAge < MAX_AGE_LIMIT ? 1 : 0) +
        (user?.nsfw_enabled && includeNsfw ? 1 : 0)

  return (
    <div className="mx-auto flex min-w-0 max-w-5xl flex-col gap-8 px-4 py-6 sm:py-8">
      <section className="min-w-0 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-neutral-200 sm:p-6">
        <div className="flex min-w-0 flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold text-gray-900 sm:text-3xl">Discover</h1>
            <p className="mt-2 text-sm text-gray-600">
              {activeTab === 'packs'
                ? 'Browse open packs, then swipe through the groups that fit your vibe.'
                : 'Refine the queue with species, city, age range, relationship style, and NSFW visibility.'}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {activeTab === 'packs' ? (
              <Link
                to="/packs/new"
                className="inline-flex items-center justify-center rounded-full bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600"
              >
                Create pack
              </Link>
            ) : null}
            <button
              type="button"
              onClick={() => setIsFilterDrawerOpen(true)}
              className="inline-flex items-center justify-center rounded-full border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
            >
              Filters
              {activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}
            </button>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-2" role="tablist" aria-label="Discover tabs">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'profiles'}
            onClick={() => handleTabChange('profiles')}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              activeTab === 'profiles'
                ? 'bg-orange-500 text-white'
                : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            Profiles
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'packs'}
            onClick={() => handleTabChange('packs')}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              activeTab === 'packs'
                ? 'bg-orange-500 text-white'
                : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            Packs
          </button>
        </div>
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          {activeTab === 'profiles' ? (
            <span className="rounded-full bg-orange-50 px-3 py-1 font-medium text-orange-700 ring-1 ring-orange-200">
              Age {minAge}-{maxAge}
            </span>
          ) : null}
          {selectedSpecies.map((value) => (
            <span
              key={value}
              className="rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-700 ring-1 ring-gray-200"
            >
              {value}
            </span>
          ))}
          {activeTab === 'profiles' && city.trim() ? (
            <span className="rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-700 ring-1 ring-gray-200">
              {city.trim()}
            </span>
          ) : null}
          {activeTab === 'profiles' && relationshipStyle ? (
            <span className="rounded-full bg-gray-100 px-3 py-1 font-medium capitalize text-gray-700 ring-1 ring-gray-200">
              {relationshipStyle}
            </span>
          ) : null}
          {activeTab === 'packs' && packSearch.trim() ? (
            <span className="rounded-full bg-gray-100 px-3 py-1 font-medium text-gray-700 ring-1 ring-gray-200">
              Search: {packSearch.trim()}
            </span>
          ) : null}
        </div>
      </section>

      {isFilterDrawerOpen ? (
        <div className="fixed inset-0 z-30 flex justify-end bg-gray-900/35 px-4 py-6 sm:px-6">
          <div
            className="w-full max-w-md overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl ring-1 ring-gray-200"
            role="dialog"
            aria-modal="true"
            aria-label="Filter drawer"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-orange-500">
                  Filter Queue
                </p>
                <h2 className="mt-2 text-2xl font-bold text-gray-900">Tune your stack</h2>
              </div>
              <button
                type="button"
                onClick={() => setIsFilterDrawerOpen(false)}
                className="rounded-full border border-gray-300 px-3 py-1 text-sm font-medium text-gray-600 transition hover:bg-gray-50"
              >
                Close
              </button>
            </div>

            <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
              <fieldset>
                <legend className="text-sm font-semibold text-gray-900">Species</legend>
                <p className="mt-1 text-sm text-gray-500">Select one or more species.</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {speciesOptions.map((option) => {
                    const isSelected = selectedSpecies.includes(option.name)
                    return (
                      <label
                        key={option.id}
                        className={`inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium transition ${
                          isSelected
                            ? 'border-orange-300 bg-orange-50 text-orange-700'
                            : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSpecies(option.name)}
                          className="h-4 w-4"
                        />
                        {option.name}
                      </label>
                    )
                  })}
                </div>
              </fieldset>

              {activeTab === 'packs' ? (
                <label
                  className="flex flex-col gap-2 text-sm font-medium text-gray-700"
                  htmlFor="pack-search"
                >
                  Search
                  <input
                    id="pack-search"
                    type="text"
                    value={packSearch}
                    onChange={(event) => setPackSearch(event.target.value)}
                    placeholder="Search pack names or descriptions"
                    className="rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900"
                  />
                </label>
              ) : (
                <>
                  <label className="flex flex-col gap-2 text-sm font-medium text-gray-700" htmlFor="city">
                    City
                    <input
                      id="city"
                      type="text"
                      value={city}
                      onChange={(event) => setCity(event.target.value)}
                      placeholder="Any city"
                      className="rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900"
                    />
                  </label>

                  <fieldset>
                    <legend className="text-sm font-semibold text-gray-900">Age range</legend>
                    <p className="mt-1 text-sm text-gray-500">
                      {minAge} to {maxAge}
                    </p>
                    <div className="mt-4 space-y-4">
                      <label
                        className="flex flex-col gap-2 text-sm font-medium text-gray-700"
                        htmlFor="min-age"
                      >
                        Minimum age
                        <input
                          id="min-age"
                          type="range"
                          min={MIN_AGE_LIMIT}
                          max={MAX_AGE_LIMIT}
                          value={minAge}
                          onChange={(event) => handleMinAgeChange(Number(event.target.value))}
                        />
                      </label>
                      <label
                        className="flex flex-col gap-2 text-sm font-medium text-gray-700"
                        htmlFor="max-age"
                      >
                        Maximum age
                        <input
                          id="max-age"
                          type="range"
                          min={MIN_AGE_LIMIT}
                          max={MAX_AGE_LIMIT}
                          value={maxAge}
                          onChange={(event) => handleMaxAgeChange(Number(event.target.value))}
                        />
                      </label>
                    </div>
                  </fieldset>

                  <label
                    className="flex flex-col gap-2 text-sm font-medium text-gray-700"
                    htmlFor="relationship-style"
                  >
                    Relationship Style
                    <select
                      id="relationship-style"
                      value={relationshipStyle}
                      onChange={(event) => setRelationshipStyle(event.target.value)}
                      className="rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900"
                    >
                      {relationshipOptions.map((option) => (
                        <option key={option.value || 'any'} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>

                  <label className="flex items-center gap-3 rounded-xl border border-gray-200 px-3 py-3 text-sm font-medium text-gray-700">
                    <input
                      type="checkbox"
                      checked={includeNsfw}
                      disabled={!user?.nsfw_enabled}
                      onChange={(event) => setIncludeNsfw(event.target.checked)}
                    />
                    Include NSFW profiles
                  </label>
                </>
              )}

              <div className="flex items-center gap-3">
                <button
                  type="submit"
                  className="rounded-full bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600"
                >
                  Apply Filters
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  className="rounded-full border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
                >
                  Reset
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      <section className="min-w-0 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-neutral-200">
        {swipeError && (
          <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
            {swipeError}
          </div>
        )}
        {loading ? (
          <p className="text-neutral-500">
            Loading {activeTab === 'packs' ? 'pack' : 'discover'} results...
          </p>
        ) : error ? (
          <p className="text-red-600">{error}</p>
        ) : candidates.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50/50 px-6 py-12 text-center">
            <p className="text-lg font-semibold text-neutral-900">
              No more {activeTab === 'packs' ? 'packs' : 'profiles'} right now.
            </p>
            <p className="mt-2 text-sm text-neutral-500">
              {activeTab === 'packs'
                ? 'Adjust your filters or check back after more packs open up.'
                : 'Adjust your filters or check back after more members join the queue.'}
            </p>
          </div>
        ) : (
          <div className="min-w-0">
            <div
              className="relative mx-auto h-[22rem] w-full min-w-0 max-w-xl sm:h-[26rem] md:h-[28rem]"
              aria-label="Swipe card stack"
            >
              {stackedCandidates
                .slice()
                .reverse()
                .map((candidate, index) => {
                  const visualIndex = stackedCandidates.length - index - 1
                  const isTopCard = visualIndex === 0
                  const isExiting = isTopCard && exitSwipe?.candidateId === candidate.id
                  const cardDragOffsetX = isExiting
                    ? exitSwipe.action === 'like'
                      ? SWIPE_EXIT_OFFSET_PX
                      : -SWIPE_EXIT_OFFSET_PX
                    : isTopCard
                      ? dragOffsetX
                      : 0

                  return (
                    <SwipeCard
                      key={candidate.id}
                      candidate={candidate}
                      isTopCard={isTopCard}
                      offsetIndex={visualIndex}
                      remainingCount={candidates.length}
                      dragOffsetX={cardDragOffsetX}
                      isDragging={isTopCard && isDragging}
                      isExiting={isExiting}
                      onTouchStart={handleCardTouchStart}
                      onTouchMove={handleCardTouchMove}
                      onTouchEnd={handleCardTouchEnd}
                      onTouchCancel={resetDragState}
                    />
                  )
                })}
              {matchOverlay && (
                <div
                  aria-label="Match overlay"
                  className="absolute inset-0 z-20 flex items-center justify-center rounded-[2rem] bg-gradient-to-br from-orange-500/95 via-pink-500/95 to-rose-600/95 p-6 text-center text-white shadow-2xl"
                >
                  <div className="max-w-sm">
                    <p className="text-xs font-semibold uppercase tracking-[0.4em] text-orange-100">
                      Mutual Like
                    </p>
                    <h2 className="mt-3 text-4xl font-black tracking-tight">It&apos;s a Match!</h2>
                    <p className="mt-3 text-sm leading-6 text-orange-50">
                      You and {matchOverlay.candidateName} liked each other. Start the conversation
                      while the spark is fresh.
                    </p>
                    <button
                      type="button"
                      onClick={() => setMatchOverlay(null)}
                      className="mt-6 rounded-full bg-white px-5 py-2 text-sm font-semibold text-rose-600 transition hover:bg-orange-50"
                    >
                      Keep swiping
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 flex min-w-0 items-center justify-center gap-4">
              <button
                type="button"
                disabled={isSubmittingSwipe || !activeCandidate || exitSwipe !== null}
                onClick={() => void handleSwipe('pass')}
                className="min-h-[52px] min-w-[52px] rounded-full border border-neutral-300 bg-transparent px-6 py-3 text-sm font-semibold text-neutral-600 transition-all duration-150 ease-out hover:scale-105 hover:border-neutral-400 hover:bg-neutral-50 hover:shadow disabled:cursor-not-allowed disabled:opacity-50"
              >
                Pass
              </button>
              <button
                type="button"
                disabled={isSubmittingSwipe || !activeCandidate || exitSwipe !== null}
                onClick={() => void handleSwipe('like')}
                className="flex min-h-[52px] min-w-[52px] items-center justify-center gap-2 rounded-full bg-gradient-to-r from-orange-500 to-amber-500 px-6 py-3 text-sm font-semibold text-white shadow-md transition-all duration-150 ease-out hover:scale-105 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-50"
              >
                <HeartIcon className="h-5 w-5" />
                Like
              </button>
            </div>
            {activeTab === 'packs' && activeCandidate && isPackCandidate(activeCandidate) ? (
              <div className="mt-4 flex justify-center">
                <Link
                  to={`/packs/${activeCandidate.id}`}
                  className="text-xs uppercase tracking-wide text-neutral-500/80 transition hover:text-neutral-700"
                >
                  View pack details
                </Link>
              </div>
            ) : null}
          </div>
        )}
      </section>

      {!loading && !error && candidates.length > 0 ? (
        <div className="min-w-0 pt-2">
          <button
            type="button"
            onClick={() => setSwipeTipsCollapsed((c) => !c)}
            className="flex w-full items-center justify-between gap-2 py-3 text-left"
            aria-expanded={!swipeTipsCollapsed}
          >
            <span className="text-xs font-medium uppercase tracking-wide text-neutral-500">
              Swipe Tips
            </span>
            <span className="text-neutral-400" aria-hidden>
              {swipeTipsCollapsed ? '▶' : '▼'}
            </span>
          </button>
          {!swipeTipsCollapsed ? (
            <ul className="max-w-2xl space-y-3 py-2 text-sm leading-relaxed text-neutral-600">
              {activeTab === 'packs' ? (
                <>
                  <li>Switch to Packs to browse open groups instead of individual profiles.</li>
                  <li>Use species and search filters to narrow the pack stack.</li>
                  <li>Pass skips the current pack and moves you to the next card.</li>
                  <li>Swipe left to pass or right to like from the top card.</li>
                </>
              ) : (
                <>
                  <li>Use filters to narrow the stack before you start swiping.</li>
                  <li>Pass skips the current profile and moves you to the next card.</li>
                  <li>Like saves a positive swipe and can create a match instantly.</li>
                  <li>Swipe left to pass or right to like from the top card.</li>
                </>
              )}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
