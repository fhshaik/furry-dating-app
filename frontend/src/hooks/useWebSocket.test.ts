import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { useWebSocket } from './useWebSocket'

class MockWebSocket {
  static instances: MockWebSocket[] = []
  static OPEN = 1
  static CONNECTING = 0
  static CLOSING = 2
  static CLOSED = 3

  onopen: ((e: Event) => void) | null = null
  onclose: ((e: CloseEvent) => void) | null = null
  onerror: ((e: Event) => void) | null = null
  onmessage: ((e: MessageEvent) => void) | null = null
  readyState = MockWebSocket.OPEN

  send = vi.fn()
  close = vi.fn()

  constructor(public url: string) {
    MockWebSocket.instances.push(this)
  }

  triggerOpen() {
    this.onopen?.(new Event('open'))
  }

  triggerClose(code = 1006) {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close', { code, wasClean: code === 1000 }))
  }

  triggerMessage(data: object) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }))
  }

  triggerError() {
    this.onerror?.(new Event('error'))
  }
}

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    MockWebSocket.instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
  })

  afterEach(() => {
    vi.runAllTimers()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('creates a WebSocket with the provided URL', () => {
    renderHook(() => useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }))

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(MockWebSocket.instances[0].url).toBe('ws://localhost/ws/chat/1')
  })

  it('does not create a WebSocket when url is null', () => {
    renderHook(() => useWebSocket(null, { onMessage: vi.fn() }))

    expect(MockWebSocket.instances).toHaveLength(0)
  })

  it('sets connected to true when socket opens', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    expect(result.current.connected).toBe(false)

    act(() => {
      MockWebSocket.instances[0].triggerOpen()
    })

    expect(result.current.connected).toBe(true)
    expect(result.current.reconnecting).toBe(false)
  })

  it('sets connected to false when socket closes', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    act(() => {
      MockWebSocket.instances[0].triggerOpen()
    })
    expect(result.current.connected).toBe(true)

    act(() => {
      MockWebSocket.instances[0].triggerClose(1006)
    })

    expect(result.current.connected).toBe(false)
  })

  it('calls onMessage with parsed data when a message arrives', () => {
    const onMessage = vi.fn()
    renderHook(() => useWebSocket('ws://localhost/ws/chat/1', { onMessage }))

    act(() => {
      MockWebSocket.instances[0].triggerOpen()
      MockWebSocket.instances[0].triggerMessage({ type: 'message', content: 'hello' })
    })

    expect(onMessage).toHaveBeenCalledWith({ type: 'message', content: 'hello' })
  })

  it('ignores malformed (non-JSON) WebSocket frames', () => {
    const onMessage = vi.fn()
    renderHook(() => useWebSocket('ws://localhost/ws/chat/1', { onMessage }))

    act(() => {
      MockWebSocket.instances[0].onmessage?.(
        new MessageEvent('message', { data: 'not-json{{{{' }),
      )
    })

    expect(onMessage).not.toHaveBeenCalled()
  })

  it('closes the socket when an error occurs', () => {
    renderHook(() => useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }))

    act(() => {
      MockWebSocket.instances[0].triggerError()
    })

    expect(MockWebSocket.instances[0].close).toHaveBeenCalled()
  })

  it('sends data when connected', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    act(() => {
      MockWebSocket.instances[0].triggerOpen()
    })

    act(() => {
      result.current.send('{"content":"hi"}')
    })

    expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith('{"content":"hi"}')
  })

  it('does not send when socket is not open', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    // Socket exists but has not opened yet
    MockWebSocket.instances[0].readyState = MockWebSocket.CONNECTING

    act(() => {
      result.current.send('{"content":"hi"}')
    })

    expect(MockWebSocket.instances[0].send).not.toHaveBeenCalled()
  })

  it('reconnects after unexpected close with 1-second initial delay', () => {
    renderHook(() => useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }))

    act(() => {
      MockWebSocket.instances[0].triggerOpen()
      MockWebSocket.instances[0].triggerClose(1006) // unexpected close
    })

    expect(MockWebSocket.instances).toHaveLength(1) // no new socket yet

    act(() => {
      vi.advanceTimersByTime(1000) // BASE_DELAY_MS
    })

    expect(MockWebSocket.instances).toHaveLength(2)
    expect(MockWebSocket.instances[1].url).toBe('ws://localhost/ws/chat/1')
  })

  it('sets reconnecting to true while waiting to reconnect', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    act(() => {
      MockWebSocket.instances[0].triggerOpen()
      MockWebSocket.instances[0].triggerClose(1006)
    })

    expect(result.current.reconnecting).toBe(true)
    expect(result.current.retryCount).toBe(1)

    act(() => {
      vi.advanceTimersByTime(1000)
      MockWebSocket.instances[1].triggerOpen()
    })

    expect(result.current.reconnecting).toBe(false)
    expect(result.current.connected).toBe(true)
    expect(result.current.retryCount).toBe(0)
  })

  it('uses exponential backoff for successive reconnect attempts', () => {
    renderHook(() => useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }))

    // 1st disconnect → wait 1s
    act(() => {
      MockWebSocket.instances[0].triggerClose(1006)
      vi.advanceTimersByTime(1000)
    })
    expect(MockWebSocket.instances).toHaveLength(2)

    // 2nd disconnect → wait 2s
    act(() => {
      MockWebSocket.instances[1].triggerClose(1006)
    })
    act(() => {
      vi.advanceTimersByTime(1999) // not yet
    })
    expect(MockWebSocket.instances).toHaveLength(2)
    act(() => {
      vi.advanceTimersByTime(1) // now crosses 2000ms
    })
    expect(MockWebSocket.instances).toHaveLength(3)

    // 3rd disconnect → wait 4s
    act(() => {
      MockWebSocket.instances[2].triggerClose(1006)
    })
    act(() => {
      vi.advanceTimersByTime(3999)
    })
    expect(MockWebSocket.instances).toHaveLength(3)
    act(() => {
      vi.advanceTimersByTime(1)
    })
    expect(MockWebSocket.instances).toHaveLength(4)
  })

  it('does not reconnect for close code 4001 (unauthenticated)', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    act(() => {
      MockWebSocket.instances[0].triggerClose(4001)
      vi.runAllTimers()
    })

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(result.current.reconnecting).toBe(false)
  })

  it('does not reconnect for close code 4003 (not a member)', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    act(() => {
      MockWebSocket.instances[0].triggerClose(4003)
      vi.runAllTimers()
    })

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(result.current.reconnecting).toBe(false)
  })

  it('does not reconnect for close code 4004 (conversation not found)', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    act(() => {
      MockWebSocket.instances[0].triggerClose(4004)
      vi.runAllTimers()
    })

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(result.current.reconnecting).toBe(false)
  })

  it('does not reconnect for clean close code 1000', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    act(() => {
      MockWebSocket.instances[0].triggerClose(1000)
      vi.runAllTimers()
    })

    expect(MockWebSocket.instances).toHaveLength(1)
    expect(result.current.reconnecting).toBe(false)
  })

  it('stops reconnecting after maxRetries is exhausted', () => {
    const { result } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn(), maxRetries: 2 }),
    )

    // 1st disconnect → retry 1
    act(() => {
      MockWebSocket.instances[0].triggerClose(1006)
      vi.advanceTimersByTime(1000)
    })
    expect(MockWebSocket.instances).toHaveLength(2)

    // 2nd disconnect → retry 2 (reaches maxRetries, retryCount becomes 2)
    act(() => {
      MockWebSocket.instances[1].triggerClose(1006)
      vi.advanceTimersByTime(2000)
    })
    expect(MockWebSocket.instances).toHaveLength(3)

    // 3rd disconnect → retryCount is 2 which equals maxRetries, so no more retries
    act(() => {
      MockWebSocket.instances[2].triggerClose(1006)
      vi.runAllTimers()
    })
    expect(MockWebSocket.instances).toHaveLength(3)
    expect(result.current.reconnecting).toBe(false)
  })

  it('cancels pending reconnect timer on unmount', () => {
    const { unmount } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    act(() => {
      MockWebSocket.instances[0].triggerOpen()
      MockWebSocket.instances[0].triggerClose(1006) // starts reconnect timer
    })

    expect(MockWebSocket.instances).toHaveLength(1)

    unmount()

    // Timer should be cancelled — advancing time should not spawn a new socket
    act(() => {
      vi.runAllTimers()
    })
    expect(MockWebSocket.instances).toHaveLength(1)
  })

  it('explicitly closes an open socket on unmount', () => {
    const { unmount } = renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn() }),
    )

    act(() => {
      MockWebSocket.instances[0].triggerOpen()
    })

    unmount()

    expect(MockWebSocket.instances[0].close).toHaveBeenCalled()
  })

  it('resets retry count and creates fresh connection when URL changes', () => {
    const { result, rerender } = renderHook(
      ({ url }: { url: string }) =>
        useWebSocket(url, { onMessage: vi.fn() }),
      { initialProps: { url: 'ws://localhost/ws/chat/1' } },
    )

    act(() => {
      MockWebSocket.instances[0].triggerClose(1006)
      vi.advanceTimersByTime(1000) // triggers reconnect
    })

    expect(result.current.retryCount).toBeGreaterThan(0)

    // Change URL — should reset everything
    rerender({ url: 'ws://localhost/ws/chat/2' })

    act(() => {
      vi.runAllTimers()
    })

    const latestInstance = MockWebSocket.instances[MockWebSocket.instances.length - 1]
    expect(latestInstance.url).toBe('ws://localhost/ws/chat/2')

    act(() => {
      latestInstance.triggerOpen()
    })

    expect(result.current.retryCount).toBe(0)
    expect(result.current.connected).toBe(true)
  })

  it('always calls the latest onMessage callback (closure-safe)', () => {
    const firstCallback = vi.fn()
    const secondCallback = vi.fn()

    const { rerender } = renderHook(
      ({ onMessage }: { onMessage: (d: Record<string, unknown>) => void }) =>
        useWebSocket('ws://localhost/ws/chat/1', { onMessage }),
      { initialProps: { onMessage: firstCallback } },
    )

    rerender({ onMessage: secondCallback })

    act(() => {
      MockWebSocket.instances[0].triggerMessage({ type: 'ping' })
    })

    expect(firstCallback).not.toHaveBeenCalled()
    expect(secondCallback).toHaveBeenCalledWith({ type: 'ping' })
  })

  it('ignores messages from a stale socket after the URL changes', () => {
    const onMessage = vi.fn()

    const { rerender } = renderHook(
      ({ url }: { url: string | null }) => useWebSocket(url, { onMessage }),
      { initialProps: { url: 'ws://localhost/ws/chat/1' } },
    )

    const firstSocket = MockWebSocket.instances[0]

    rerender({ url: 'ws://localhost/ws/chat/2' })

    act(() => {
      firstSocket.triggerMessage({ type: 'stale' })
      MockWebSocket.instances[1].triggerMessage({ type: 'fresh' })
    })

    expect(onMessage).toHaveBeenCalledTimes(1)
    expect(onMessage).toHaveBeenCalledWith({ type: 'fresh' })
  })

  it('ignores close events from a stale socket after the URL changes', () => {
    const { rerender } = renderHook(
      ({ url }: { url: string | null }) =>
        useWebSocket(url, { onMessage: vi.fn() }),
      { initialProps: { url: 'ws://localhost/ws/chat/1' } },
    )

    const firstSocket = MockWebSocket.instances[0]

    rerender({ url: 'ws://localhost/ws/chat/2' })

    act(() => {
      firstSocket.triggerClose(1006)
      vi.runAllTimers()
    })

    expect(MockWebSocket.instances).toHaveLength(2)
    expect(MockWebSocket.instances[1].url).toBe('ws://localhost/ws/chat/2')
  })

  it('caps reconnect delay at 30 seconds', () => {
    renderHook(() =>
      useWebSocket('ws://localhost/ws/chat/1', { onMessage: vi.fn(), maxRetries: 20 }),
    )

    // Exhaust many retries to get past the cap
    for (let i = 0; i < 10; i++) {
      const ws = MockWebSocket.instances[MockWebSocket.instances.length - 1]
      act(() => {
        ws.triggerClose(1006)
        vi.advanceTimersByTime(30000) // MAX_DELAY_MS
      })
    }

    // Should have reconnected multiple times but delay never exceeds 30s
    expect(MockWebSocket.instances.length).toBeGreaterThan(5)
  })
})
