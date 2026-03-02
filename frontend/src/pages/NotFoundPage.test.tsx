import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import NotFoundPage from './NotFoundPage'

function renderNotFound() {
  return render(
    <MemoryRouter>
      <NotFoundPage />
    </MemoryRouter>,
  )
}

describe('NotFoundPage', () => {
  it('renders the 404 heading', () => {
    renderNotFound()
    expect(screen.getByRole('heading', { name: /404/i })).toBeInTheDocument()
  })

  it('renders the "Page not found" message', () => {
    renderNotFound()
    expect(screen.getByText(/Page not found/i)).toBeInTheDocument()
  })

  it('renders a link to the home page', () => {
    renderNotFound()
    const link = screen.getByRole('link', { name: /go home/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/')
  })
})
