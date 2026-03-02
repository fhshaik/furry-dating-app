import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import PackCard from './PackCard'

describe('PackCard', () => {
  it('renders the pack image, name, member count, and species tags', () => {
    render(
      <PackCard
        name="Moon Pack"
        imageUrl="https://example.com/moon-pack.jpg"
        memberCount={3}
        speciesTags={['Wolf', 'Fox']}
      />,
    )

    expect(screen.getByRole('img', { name: /moon pack pack/i })).toHaveAttribute(
      'src',
      'https://example.com/moon-pack.jpg',
    )
    expect(screen.getByRole('heading', { name: 'Moon Pack' })).toBeInTheDocument()
    expect(screen.getByText('3 members')).toBeInTheDocument()
    expect(screen.getByText('Wolf')).toBeInTheDocument()
    expect(screen.getByText('Fox')).toBeInTheDocument()
  })

  it('renders fallbacks when image and species tags are missing', () => {
    render(<PackCard name="Sun Pack" imageUrl={null} memberCount={null} speciesTags={null} />)

    expect(screen.queryByRole('img', { name: /sun pack pack/i })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sun Pack' })).toBeInTheDocument()
    expect(screen.getByText('0 members')).toBeInTheDocument()
    expect(screen.getByText('Species tags pending')).toBeInTheDocument()
    expect(screen.getByText('S')).toBeInTheDocument()
  })
})
