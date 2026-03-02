import { Link } from 'react-router-dom'

export interface PackCardProps {
  name: string
  imageUrl: string | null
  memberCount: number | null
  speciesTags: string[] | null
  packId?: number
  conversationId?: number | null
}

function getMemberCountLabel(memberCount: number | null) {
  const count = memberCount ?? 0

  return `${count} member${count === 1 ? '' : 's'}`
}

export default function PackCard({
  name,
  imageUrl,
  memberCount,
  speciesTags,
  packId,
  conversationId,
}: PackCardProps) {
  const imageBlock = (
    <div className="relative min-h-64 overflow-hidden bg-[#f0cb98]">
      {imageUrl ? (
        <img src={imageUrl} alt={`${name} pack`} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full min-h-64 items-center justify-center bg-linear-to-br from-[#f7d5ad] via-[#d98a59] to-[#7b3b46]">
          <span className="font-['Copperplate','Georgia',serif] text-6xl font-black uppercase tracking-[0.2em] text-white/85">
            {name.charAt(0)}
          </span>
        </div>
      )}
      <div className="absolute inset-x-0 bottom-0 bg-linear-to-t from-[#241419]/80 to-transparent px-6 py-5 text-white">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[#ffd7a8]">Pack</p>
        <h2 className="mt-2 font-['Copperplate','Georgia',serif] text-3xl font-bold">{name}</h2>
        <p className="mt-2 text-sm font-medium text-[#ffe8cf]">{getMemberCountLabel(memberCount)}</p>
      </div>
    </div>
  )

  return (
    <section className="h-full overflow-hidden rounded-[2.2rem] border border-[#f0c796] bg-linear-to-br from-[#fff7ea] via-[#f7dfbf] to-[#fff0dc] shadow-[0_24px_60px_rgba(33,14,23,0.22)]">
      {packId != null ? <Link to={`/packs/${packId}`} className="block">{imageBlock}</Link> : imageBlock}

      <div className="p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[#8b6459]">Species Tags</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {speciesTags && speciesTags.length > 0 ? (
            speciesTags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-[#efc796] bg-white/85 px-3 py-1 text-xs font-semibold text-[#5d3241]"
              >
                {tag}
              </span>
            ))
          ) : (
            <span className="rounded-full border border-[#edd7bf] bg-white/85 px-3 py-1 text-xs font-semibold text-[#836764]">
              Species tags pending
            </span>
          )}
        </div>
        {conversationId != null ? (
          <div className="mt-4">
            <Link
              to={`/inbox/${conversationId}`}
              className="inline-flex items-center gap-2 rounded-full bg-[#7d3352] px-4 py-2 text-sm font-semibold text-white transition hover:bg-[#5f2740]"
            >
              💬 Pack chat
            </Link>
          </div>
        ) : null}
      </div>
    </section>
  )
}
