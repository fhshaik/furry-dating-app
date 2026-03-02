import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import SwipeCard from './SwipeCard'

describe('SwipeCard', () => {
  it('shows fursona image, species, and traits when available', () => {
    render(
      <SwipeCard
        candidate={{
          id: 7,
          display_name: 'River',
          bio: 'Coffee and conventions.',
          age: 29,
          city: 'Portland',
          relationship_style: 'monogamous',
          fursona: {
            name: 'Cinder',
            species: 'Fox',
            traits: ['playful', 'creative'],
            image_url: 'https://example.com/cinder.jpg',
          },
        }}
        isTopCard
        offsetIndex={0}
        remainingCount={3}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Cinder' })).toBeInTheDocument()
    expect(screen.getByText('Fox')).toBeInTheDocument()
    expect(screen.getByText(/Playful/)).toBeInTheDocument()
    expect(screen.getByText(/Creative/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /cinder fursona/i })).toHaveAttribute(
      'src',
      'https://example.com/cinder.jpg',
    )
  })

  it('renders fallback content when fursona details are missing', () => {
    render(
      <SwipeCard
        candidate={{
          id: 8,
          display_name: 'Nova',
          bio: null,
          age: null,
          city: null,
          relationship_style: null,
          fursona: null,
        }}
        isTopCard
        offsetIndex={0}
        remainingCount={1}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Nova' })).toBeInTheDocument()
    expect(screen.getByText('Species unknown')).toBeInTheDocument()
    expect(screen.getByText('Traits pending')).toBeInTheDocument()
    expect(screen.getByText('No bio yet. Swipe to keep the queue moving.')).toBeInTheDocument()
  })

  it('fades the card while animating out after a swipe', () => {
    render(
      <SwipeCard
        candidate={{
          id: 9,
          display_name: 'Echo',
          bio: 'Late-night arcade runs.',
          age: 31,
          city: 'Austin',
          relationship_style: 'open',
          fursona: null,
        }}
        isTopCard
        offsetIndex={0}
        remainingCount={2}
        dragOffsetX={420}
        isExiting
      />,
    )

    const card = screen.getByRole('heading', { name: 'Echo' }).closest('article')

    expect(card).not.toBeNull()
    expect(card as HTMLElement).toHaveStyle({ opacity: '0' })
    expect((card as HTMLElement).style.transform).toContain('translateX(420px)')
  })

  it('renders pack details when the candidate is a pack', () => {
    render(
      <SwipeCard
        candidate={{
          id: 10,
          type: 'pack',
          name: 'Moon Pack',
          description: 'Open to hikers, gamers, and cozy den nights.',
          image_url: 'https://example.com/moon-pack.jpg',
          species_tags: ['Wolf', 'Fox'],
          max_size: 6,
          member_count: 4,
          is_open: true,
          consensus_required: true,
        }}
        isTopCard
        offsetIndex={0}
        remainingCount={2}
      />,
    )

    expect(screen.getByRole('heading', { name: 'Moon Pack' })).toBeInTheDocument()
    expect(screen.getByText(/Wolf/)).toBeInTheDocument()
    expect(screen.getByText(/Fox/)).toBeInTheDocument()
    expect(screen.getByText('4 members')).toBeInTheDocument()
    expect(screen.getByText(/4\/6 members/)).toBeInTheDocument()
    expect(screen.getByText(/Consensus required/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /moon pack pack/i })).toHaveAttribute(
      'src',
      'https://example.com/moon-pack.jpg',
    )
  })
})
