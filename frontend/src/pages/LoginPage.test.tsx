import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from './LoginPage'

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  it('renders the FurConnect heading', () => {
    renderLoginPage()
    expect(screen.getByRole('heading', { name: /FurConnect/i })).toBeInTheDocument()
  })

  it('renders the tagline', () => {
    renderLoginPage()
    expect(screen.getByText(/Find your pack/i)).toBeInTheDocument()
  })

  it('renders the Sign in with Google link pointing to /api/auth/google', () => {
    renderLoginPage()
    const link = screen.getByRole('link', { name: /sign in with google/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/api/auth/google')
  })

  it('renders the Sign in with Discord link pointing to /api/auth/discord', () => {
    renderLoginPage()
    const link = screen.getByRole('link', { name: /sign in with discord/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', '/api/auth/discord')
  })
})
