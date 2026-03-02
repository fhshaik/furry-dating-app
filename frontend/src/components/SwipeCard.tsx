import type { TouchEventHandler } from 'react'

interface SwipeCardFursona {
  name: string
  species: string | null
  traits: string[] | null
  image_url: string | null
}

interface SwipeCardUserCandidate {
  id: number
  type?: 'user'
  display_name: string
  bio: string | null
  age: number | null
  city: string | null
  relationship_style: string | null
  fursona?: SwipeCardFursona | null
}

export interface SwipeCardPackCandidate {
  id: number
  type: 'pack'
  name: string
  description: string | null
  image_url: string | null
  species_tags: string[] | null
  max_size: number | null
  member_count?: number | null
  is_open?: boolean
  consensus_required?: boolean
}

export type SwipeCardCandidate = SwipeCardUserCandidate | SwipeCardPackCandidate

interface SwipeCardProps {
  candidate: SwipeCardCandidate
  isTopCard: boolean
  offsetIndex: number
  remainingCount: number
  dragOffsetX?: number
  isDragging?: boolean
  isExiting?: boolean
  onTouchStart?: TouchEventHandler<HTMLElement>
  onTouchMove?: TouchEventHandler<HTMLElement>
  onTouchEnd?: TouchEventHandler<HTMLElement>
  onTouchCancel?: TouchEventHandler<HTMLElement>
}

function formatTrait(trait: string) {
  return trait.charAt(0).toUpperCase() + trait.slice(1)
}

function isPackCandidate(candidate: SwipeCardCandidate): candidate is SwipeCardPackCandidate {
  return candidate.type === 'pack'
}

function PackMetadataInline({
  memberCount,
  maxSize,
  isOpen,
  consensusRequired,
}: {
  memberCount: number | null
  maxSize: number | null
  isOpen: boolean | undefined
  consensusRequired: boolean | undefined
}) {
  const count = memberCount ?? 0
  const size = maxSize ?? '?'
  const parts: string[] = []
  parts.push(`${count}/${size} members`)
  parts.push(isOpen === false ? 'Invite only' : 'Open pack')
  parts.push(consensusRequired ? 'Consensus required' : 'Leader approval')
  return (
    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8c6a5c]" aria-label="Pack metadata">
      {parts.join(' • ')}
    </p>
  )
}

function UserMetadataInline({
  city,
  relationshipStyle,
  age,
}: {
  city: string | null
  relationshipStyle: string | null
  age: number | null
}) {
  const parts: string[] = []
  if (city) parts.push(city)
  if (relationshipStyle) parts.push(relationshipStyle)
  if (age != null) parts.push(`${age}`)
  if (parts.length === 0) {
    return <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8c6a5c]">Location & style not set</p>
  }
  return (
    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8c6a5c]" aria-label="Profile metadata">
      {parts.join(' • ')}
    </p>
  )
}

export default function SwipeCard({
  candidate,
  isTopCard,
  offsetIndex,
  remainingCount,
  dragOffsetX = 0,
  isDragging = false,
  isExiting = false,
  onTouchStart,
  onTouchMove,
  onTouchEnd,
  onTouchCancel,
}: SwipeCardProps) {
  const isPack = isPackCandidate(candidate)
  const fursona = isPack ? null : candidate.fursona
  const cardName = isPack ? candidate.name : fursona?.name || candidate.display_name
  const speciesLabel = fursona?.species || 'Species unknown'
  const traits = isPack ? [] : fursona?.traits ?? []
  const imageUrl = isPack ? candidate.image_url : fursona?.image_url
  const summaryText = isPack
    ? candidate.description ?? 'No pack description yet. Swipe to keep the queue moving.'
    : candidate.bio ?? 'No bio yet. Swipe to keep the queue moving.'

  const rotation = isTopCard ? dragOffsetX / 18 : 0
  const baseTranslateY = offsetIndex * 14
  const scale = 1 - offsetIndex * 0.04

  const memberCountNum = isPack ? (candidate.member_count ?? 0) : 0
  const memberCountLabel = isPack ? `${memberCountNum} member${memberCountNum === 1 ? '' : 's'}` : null

  return (
    <article
      className={`absolute inset-0 flex flex-col overflow-hidden rounded-[2rem] border bg-[linear-gradient(180deg,rgba(255,249,239,0.97),rgba(252,232,206,0.9))] shadow-[0_22px_50px_rgba(32,14,23,0.22)] ${
        isDragging ? '' : 'transition-[transform,opacity] duration-300 ease-out'
      } ${isTopCard ? 'border-[#efc89a]' : 'border-[#f3dcc2]'}`}
      style={{
        transform: `translateX(${isTopCard ? dragOffsetX : 0}px) translateY(${baseTranslateY}px) rotate(${rotation}deg) scale(${scale})`,
        opacity: isExiting ? 0 : 1,
        touchAction: isTopCard ? 'pan-y' : undefined,
      }}
      aria-hidden={!isTopCard}
      onTouchStart={isTopCard ? onTouchStart : undefined}
      onTouchMove={isTopCard ? onTouchMove : undefined}
      onTouchEnd={isTopCard ? onTouchEnd : undefined}
      onTouchCancel={isTopCard ? onTouchCancel : undefined}
    >
      {/* PRIMARY: Hero image full-bleed, aspect 4:5, gradient overlay bottom only */}
      <div className="relative aspect-[4/5] w-full shrink-0 overflow-hidden bg-[#f4d4ab]">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={isPack ? `${cardName} pack` : `${cardName} fursona`}
            className="h-full w-full object-cover"
          />
        ) : (
          <div
            className="flex h-full w-full items-center justify-center bg-[linear-gradient(135deg,#f7d3a8,#df8c5b,#8e4b4d)]"
            aria-hidden
          >
            <span className="font-['Copperplate','Georgia',serif] text-5xl font-bold text-white/85" aria-hidden>
              {cardName.charAt(0)}
            </span>
          </div>
        )}
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#241419]/75 via-[#241419]/20 to-transparent px-6 py-5 text-white">
          <div className="flex items-end justify-between gap-4">
            <h2 className="font-['Copperplate','Georgia',serif] text-3xl font-bold leading-tight">{cardName}</h2>
            {isPack && memberCountLabel ? (
              <span className="shrink-0 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white/95">
                {memberCountLabel}
              </span>
            ) : (
              <span className="shrink-0 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-white/95">
                {speciesLabel}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* SECONDARY + TERTIARY: Single content block, 24px padding, 16px vertical rhythm */}
      <div className="flex min-h-0 flex-1 flex-col p-6">
        <p className="line-clamp-3 text-base leading-7 text-[#63494b]">{summaryText}</p>

        {/* Tertiary: inline metadata, no pills */}
        <div className="mt-4">
          {isPack ? (
            <PackMetadataInline
              memberCount={candidate.member_count ?? null}
              maxSize={candidate.max_size ?? null}
              isOpen={candidate.is_open}
              consensusRequired={candidate.consensus_required}
            />
          ) : (
            <UserMetadataInline
              city={candidate.city}
              relationshipStyle={candidate.relationship_style}
              age={candidate.age}
            />
          )}
        </div>

        {/* Tags: subtle, not pills */}
        {isPack && candidate.species_tags && candidate.species_tags.length > 0 ? (
          <p className="mt-3 text-xs font-semibold uppercase tracking-[0.24em] text-[#8c6a5c]">
            {candidate.species_tags.join(' · ')}
          </p>
        ) : null}
        {!isPack && traits.length > 0 ? (
          <p className="mt-3 text-xs font-semibold uppercase tracking-[0.24em] text-[#8c6a5c]">
            {traits.map(formatTrait).join(' · ')}
          </p>
        ) : null}
        {!isPack && traits.length === 0 ? (
          <p className="mt-3 text-xs font-semibold uppercase tracking-[0.24em] text-[#8c6a5c]">Traits pending</p>
        ) : null}

        {/* Stack count: no bordered box, optional divider */}
        <div className="mt-5 border-t border-[#ebcfaf] pt-4">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8c6a5c]">
            {remainingCount} profile{remainingCount === 1 ? '' : 's'} remaining
          </p>
        </div>
      </div>
    </article>
  )
}
