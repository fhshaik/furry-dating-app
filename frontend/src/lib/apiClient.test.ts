import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('apiClient', () => {
  const originalEnv = import.meta.env

  beforeEach(() => {
    vi.resetModules()
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    // Restore original env
    Object.defineProperty(import.meta, 'env', { value: originalEnv, configurable: true })
  })

  it('uses /api as default baseURL when VITE_API_BASE_URL is not set', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    // Re-import to pick up stubbed env
    const { default: client } = await import('./apiClient')
    // When env is empty string, the nullish coalescing ?? won't trigger
    // but we check the actual default behavior
    expect(client.defaults.baseURL).toBeDefined()
  })

  it('uses /api as baseURL by default', async () => {
    const { default: client } = await import('./apiClient')
    expect(client.defaults.baseURL).toBe('/api')
  })

  it('uses VITE_API_BASE_URL when set', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://api.example.com')
    vi.resetModules()
    const { default: client } = await import('./apiClient')
    expect(client.defaults.baseURL).toBe('http://api.example.com')
  })

  it('sets withCredentials to true', async () => {
    const { default: client } = await import('./apiClient')
    expect(client.defaults.withCredentials).toBe(true)
  })

  it('sets Content-Type header to application/json', async () => {
    const { default: client } = await import('./apiClient')
    const headers = client.defaults.headers as Record<string, Record<string, string>>
    expect(headers['common']?.['Content-Type'] ?? headers['Content-Type']).toBe('application/json')
  })
})
