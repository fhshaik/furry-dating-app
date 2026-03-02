import { useCallback, useEffect, useRef, useState } from 'react'

interface UseWebSocketOptions {
  onMessage: (data: Record<string, unknown>) => void
  maxRetries?: number
}

interface UseWebSocketReturn {
  connected: boolean
  reconnecting: boolean
  retryCount: number
  send: (data: string) => void
}

// Close codes where reconnecting would not help (auth/authorization errors, clean close)
const NO_RECONNECT_CODES = new Set([4001, 4003, 4004, 1000, 1001])
const BASE_DELAY_MS = 1000
const MAX_DELAY_MS = 30000

export function useWebSocket(
  url: string | null,
  { onMessage, maxRetries = 10 }: UseWebSocketOptions,
): UseWebSocketReturn {
  const [connected, setConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const unmountedRef = useRef(false)

  // Keep onMessage ref in sync so reconnected sockets always call the latest callback
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    if (!url) return
    const socketUrl = url

    unmountedRef.current = false
    retryCountRef.current = 0

    function connect() {
      if (unmountedRef.current) return

      timerRef.current = null

      const ws = new WebSocket(socketUrl)
      wsRef.current = ws

      ws.onopen = () => {
        if (unmountedRef.current || wsRef.current !== ws) {
          ws.close()
          return
        }
        retryCountRef.current = 0
        setRetryCount(0)
        setConnected(true)
        setReconnecting(false)
      }

      ws.onclose = (event) => {
        if (unmountedRef.current || wsRef.current !== ws) return
        setConnected(false)
        wsRef.current = null

        const shouldReconnect =
          !NO_RECONNECT_CODES.has(event.code) && retryCountRef.current < maxRetries

        if (shouldReconnect) {
          const delay = Math.min(BASE_DELAY_MS * Math.pow(2, retryCountRef.current), MAX_DELAY_MS)
          retryCountRef.current += 1
          setRetryCount(retryCountRef.current)
          setReconnecting(true)
          timerRef.current = setTimeout(connect, delay)
        } else {
          setReconnecting(false)
        }
      }

      ws.onerror = () => {
        if (wsRef.current === ws) {
          ws.close()
        }
      }

      ws.onmessage = (event: MessageEvent) => {
        if (wsRef.current !== ws) return
        try {
          const data = JSON.parse(event.data as string) as Record<string, unknown>
          onMessageRef.current(data)
        } catch {
          // ignore malformed frames
        }
      }
    }

    connect()

    return () => {
      unmountedRef.current = true
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current)
        timerRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setConnected(false)
      setReconnecting(false)
      retryCountRef.current = 0
      setRetryCount(0)
    }
  }, [url, maxRetries])

  const send = useCallback((data: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data)
    }
  }, [])

  return { connected, reconnecting, retryCount, send }
}
