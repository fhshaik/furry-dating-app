import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import apiClient from '../lib/apiClient'
import { useAuth } from '../contexts/AuthContext'

interface PackDetailMember {
  user: {
    id: number
    display_name: string
  }
  role: 'admin' | 'member'
  joined_at: string
}

interface PackDetailResponse {
  id: number
  creator_id: number
  name: string
  description: string | null
  image_url: string | null
  species_tags: string[] | null
  max_size: number
  consensus_required: boolean
  is_open: boolean
  created_at: string
  members: PackDetailMember[]
  conversation_id: number | null
}

interface JoinRequestVote {
  voter_user_id: number
  decision: 'approved' | 'denied'
  user: { id: number; display_name: string }
}

interface JoinRequest {
  id: number
  pack_id: number
  user_id: number
  status: 'pending' | 'approved' | 'denied'
  created_at: string
  user: { id: number; display_name: string }
  votes: JoinRequestVote[]
  approvals_required: number
  approvals_received: number
}

function formatRoleLabel(role: PackDetailMember['role']) {
  return role === 'admin' ? 'Admin' : 'Member'
}

function formatJoinedDate(joinedAt: string) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(joinedAt))
}

export default function PackDetailPage() {
  const { packId } = useParams<{ packId: string }>()
  const { user } = useAuth()
  const [pack, setPack] = useState<PackDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSubmittingJoin, setIsSubmittingJoin] = useState(false)
  const [joinRequestSent, setJoinRequestSent] = useState(false)
  const [joinError, setJoinError] = useState<string | null>(null)

  const [joinRequests, setJoinRequests] = useState<JoinRequest[]>([])
  const [joinRequestsLoading, setJoinRequestsLoading] = useState(false)
  const [actionInProgress, setActionInProgress] = useState<Set<string>>(new Set())

  const fetchPack = useCallback(() => {
    return apiClient.get<PackDetailResponse>(`/packs/${packId}`)
  }, [packId])

  const fetchJoinRequests = useCallback(
    (currentPackId: number) => {
      setJoinRequestsLoading(true)
      apiClient
        .get<JoinRequest[]>(`/packs/${currentPackId}/join-requests`)
        .then((res) => {
          setJoinRequests(res.data)
        })
        .catch(() => {
          setJoinRequests([])
        })
        .finally(() => {
          setJoinRequestsLoading(false)
        })
    },
    [],
  )

  useEffect(() => {
    let isMounted = true

    setLoading(true)
    setError(null)
    setJoinError(null)
    setJoinRequestSent(false)

    fetchPack()
      .then((response) => {
        if (!isMounted) {
          return
        }

        setPack(response.data)
      })
      .catch(() => {
        if (!isMounted) {
          return
        }

        setPack(null)
        setError('Failed to load pack details.')
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false)
        }
      })

    return () => {
      isMounted = false
    }
  }, [packId, fetchPack])

  const isMember = pack?.members.some((member) => member.user.id === user?.id) ?? false
  const adminMembership = pack?.members.find(
    (member) => member.user.id === user?.id && member.role === 'admin',
  )
  const memberCount = pack?.members.length ?? 0
  const canJoin = Boolean(pack && !isMember && pack.is_open && !joinRequestSent)
  const canEdit = Boolean(adminMembership)
  const canManageRequests = Boolean(
    pack && (canEdit || (pack.consensus_required && isMember)),
  )

  useEffect(() => {
    if (pack && canManageRequests) {
      fetchJoinRequests(pack.id)
    }
  }, [pack, canManageRequests, fetchJoinRequests])

  async function handleJoin() {
    if (!pack || !canJoin) {
      return
    }

    setIsSubmittingJoin(true)
    setJoinError(null)

    try {
      await apiClient.post(`/packs/${pack.id}/join-request`)
      setJoinRequestSent(true)
    } catch {
      setJoinError('Failed to send join request.')
    } finally {
      setIsSubmittingJoin(false)
    }
  }

  async function handleDecide(targetUserId: number, decision: 'approved' | 'denied') {
    if (!pack) return
    const key = `decide-${targetUserId}`
    setActionInProgress((prev) => new Set(prev).add(key))
    try {
      await apiClient.patch(`/packs/${pack.id}/join-requests/${targetUserId}`, {
        status: decision,
      })
      // Re-fetch both so member list and requests stay in sync
      const [packRes] = await Promise.all([
        fetchPack(),
        Promise.resolve(fetchJoinRequests(pack.id)),
      ])
      setPack(packRes.data)
    } catch {
      // silently ignore — requests list will remain unchanged
    } finally {
      setActionInProgress((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    }
  }

  async function handleRemoveMember(targetUserId: number) {
    if (!pack) return
    const key = `remove-${targetUserId}`
    setActionInProgress((prev) => new Set(prev).add(key))
    try {
      await apiClient.delete(`/packs/${pack.id}/members/${targetUserId}`)
      const packRes = await fetchPack()
      setPack(packRes.data)
    } catch {
      // silently ignore
    } finally {
      setActionInProgress((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    }
  }

  return (
    <section className="mx-auto flex min-h-full w-full max-w-5xl flex-col gap-6 px-4 py-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-orange-500">Pack Detail</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-gray-900">
            {loading ? 'Loading pack...' : pack?.name ?? 'Pack not available'}
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {pack && isMember && pack.conversation_id != null ? (
            <Link
              to={`/inbox/${pack.conversation_id}`}
              className="rounded-full bg-indigo-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-600"
            >
              💬 Open pack chat
            </Link>
          ) : null}
          {pack && canEdit ? (
            <Link
              to={`/packs/${pack.id}/edit`}
              className="rounded-full bg-orange-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-orange-600"
            >
              Edit pack
            </Link>
          ) : null}
          <Link
            to="/packs"
            className="rounded-full border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
          >
            Back to packs
          </Link>
        </div>
      </div>

      {loading ? (
        <p className="rounded-2xl border border-gray-200 bg-white px-4 py-6 text-sm text-gray-600">
          Loading pack details...
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

      {!loading && !error && pack ? (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(18rem,0.8fr)]">
          <article className="overflow-hidden rounded-[2rem] border border-orange-200 bg-white shadow-sm">
            <div className="relative min-h-72 overflow-hidden bg-orange-100">
              {pack.image_url ? (
                <img src={pack.image_url} alt={`${pack.name} pack`} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full min-h-72 items-center justify-center bg-linear-to-br from-orange-200 via-amber-100 to-white">
                  <span className="text-7xl font-black uppercase tracking-[0.2em] text-orange-500/70">
                    {pack.name.charAt(0)}
                  </span>
                </div>
              )}
              <div className="absolute inset-x-0 bottom-0 bg-linear-to-t from-black/60 to-transparent px-6 py-5 text-white">
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-orange-100">
                  {pack.is_open ? 'Open Pack' : 'Invite Only'}
                </p>
                <h2 className="mt-2 text-3xl font-bold">{pack.name}</h2>
                <p className="mt-2 text-sm font-medium text-orange-50">
                  {memberCount}/{pack.max_size} members
                </p>
              </div>
            </div>

            <div className="space-y-6 p-6">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-gray-500">Description</p>
                <p className="mt-3 text-sm leading-7 text-gray-700">
                  {pack.description ?? 'No pack description yet.'}
                </p>
              </div>

              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-gray-500">Species Tags</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {pack.species_tags && pack.species_tags.length > 0 ? (
                    pack.species_tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-orange-50 px-3 py-1 text-xs font-semibold text-orange-700 ring-1 ring-orange-200"
                      >
                        {tag}
                      </span>
                    ))
                  ) : (
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-gray-500 ring-1 ring-gray-200">
                      Species tags pending
                    </span>
                  )}
                </div>
              </div>
            </div>
          </article>

          <aside className="space-y-6">
            {!isMember ? (
              <div className="rounded-3xl border border-gray-200 bg-gray-50 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.25em] text-gray-500">Join Pack</p>
                <p className="mt-3 text-sm leading-6 text-gray-600">
                  {pack.consensus_required
                    ? 'Every current member needs to approve new join requests.'
                    : 'Pack admins review join requests before adding new members.'}
                </p>
                <button
                  type="button"
                  onClick={() => void handleJoin()}
                  disabled={!canJoin || isSubmittingJoin}
                  className="mt-5 w-full rounded-full bg-orange-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSubmittingJoin
                    ? 'Sending request...'
                    : joinRequestSent
                      ? 'Request sent'
                      : pack.is_open
                        ? 'Request to join'
                        : 'Invite only'}
                </button>
                {joinError ? <p className="mt-3 text-sm text-red-600">{joinError}</p> : null}
              </div>
            ) : null}

            {canManageRequests ? (
              <div className="rounded-3xl border border-orange-200 bg-orange-50 p-5">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.25em] text-orange-700">
                    Pending Requests
                  </p>
                  {joinRequests.length > 0 ? (
                    <span className="rounded-full bg-orange-500 px-2.5 py-0.5 text-xs font-bold text-white">
                      {joinRequests.length}
                    </span>
                  ) : null}
                </div>
                {joinRequestsLoading ? (
                  <p className="mt-3 text-sm text-orange-700/70">Loading requests...</p>
                ) : joinRequests.length === 0 ? (
                  <p className="mt-3 text-sm text-orange-700/70">No pending join requests.</p>
                ) : (
                  <ul className="mt-4 space-y-3" aria-label="Pending join requests">
                    {joinRequests.map((req) => {
                      const isActing =
                        actionInProgress.has(`decide-${req.user_id}`)
                      return (
                        <li
                          key={req.id}
                          className="rounded-2xl border border-orange-200 bg-white p-4"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="truncate font-semibold text-gray-900">
                                {req.user.display_name}
                              </p>
                              {pack.consensus_required ? (
                                <>
                                  <p className="mt-0.5 text-xs text-gray-500">
                                    {req.approvals_received}/{req.approvals_required} approvals
                                  </p>
                                  <div
                                    className="mt-2 flex flex-wrap gap-1.5"
                                    aria-label="Vote breakdown"
                                  >
                                    {req.votes.map((vote) => (
                                      <span
                                        key={vote.voter_user_id}
                                        className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                                          vote.decision === 'approved'
                                            ? 'bg-green-100 text-green-700'
                                            : 'bg-red-100 text-red-700'
                                        }`}
                                      >
                                        {vote.user.display_name}:{' '}
                                        {vote.decision === 'approved' ? 'Approved' : 'Denied'}
                                      </span>
                                    ))}
                                    {pack.members
                                      .filter(
                                        (m) =>
                                          !req.votes.some((v) => v.voter_user_id === m.user.id),
                                      )
                                      .map((m) => (
                                        <span
                                          key={m.user.id}
                                          className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-semibold text-gray-500"
                                        >
                                          {m.user.display_name}: Pending
                                        </span>
                                      ))}
                                  </div>
                                </>
                              ) : null}
                            </div>
                            <div className="flex shrink-0 gap-2">
                              <button
                                type="button"
                                aria-label={`Approve ${req.user.display_name}`}
                                onClick={() => void handleDecide(req.user_id, 'approved')}
                                disabled={isActing}
                                className="rounded-full bg-green-500 px-3 py-1 text-xs font-semibold text-white transition hover:bg-green-600 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                Approve
                              </button>
                              <button
                                type="button"
                                aria-label={`Deny ${req.user.display_name}`}
                                onClick={() => void handleDecide(req.user_id, 'denied')}
                                disabled={isActing}
                                className="rounded-full bg-red-500 px-3 py-1 text-xs font-semibold text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                Deny
                              </button>
                            </div>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                )}
              </div>
            ) : null}

            <div className="rounded-3xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.25em] text-gray-500">Members</p>
                  <h2 className="mt-2 text-xl font-semibold text-gray-900">{memberCount} in the den</h2>
                </div>
                <span className="rounded-full bg-orange-50 px-3 py-1 text-xs font-semibold text-orange-700 ring-1 ring-orange-200">
                  {pack.consensus_required ? 'Consensus' : 'Admin review'}
                </span>
              </div>

              <ul className="mt-5 space-y-3" aria-label="Pack members">
                {pack.members.map((member) => {
                  const isRemoving = actionInProgress.has(`remove-${member.user.id}`)
                  const canRemove = canEdit && member.user.id !== user?.id
                  return (
                    <li
                      key={member.user.id}
                      className="flex items-center justify-between gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3"
                    >
                      <div>
                        <p className="font-semibold text-gray-900">{member.user.display_name}</p>
                        <p className="text-sm text-gray-500">Joined {formatJoinedDate(member.joined_at)}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-gray-700 ring-1 ring-gray-200">
                          {formatRoleLabel(member.role)}
                        </span>
                        {canRemove ? (
                          <button
                            type="button"
                            aria-label={`Remove ${member.user.display_name}`}
                            onClick={() => void handleRemoveMember(member.user.id)}
                            disabled={isRemoving}
                            className="rounded-full bg-red-50 px-3 py-1 text-xs font-semibold text-red-600 ring-1 ring-red-200 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {isRemoving ? 'Removing...' : 'Remove'}
                          </button>
                        ) : null}
                      </div>
                    </li>
                  )
                })}
              </ul>
            </div>
          </aside>
        </div>
      ) : null}
    </section>
  )
}
