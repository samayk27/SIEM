// ===================
// ©AngelaMos | 2026
// useEventStream.ts
//
// SSE hooks that connect to the live log and alert streams
//
// useLogStream and useAlertStream each open an EventSource connection to the
// backend. Because EventSource doesn't support custom headers, the JWT is
// passed as a URL query parameter. On error the connection closes and
// reconnects after 3 seconds. Events are pushed into the stream store's
// ring buffers. Both hooks clean up their connection on unmount.
//
// Key exports:
//   useLogStream - connects to /logs/stream and pushes events into streamStore
//   useAlertStream - connects to /alerts/stream and pushes events into streamStore
//
// Connects to:
//   stream.store.ts - pushLogEvent, pushAlertEvent, setLogConnected, setAlertConnected
//   auth.store.ts - reads accessToken for the URL query param
//   api.ts - getBaseURL() for SSE URL construction
// ===================

import { useCallback, useEffect, useRef } from 'react'
import type { StreamAlertEvent, StreamLogEvent } from '@/api/types'
import { API_ENDPOINTS } from '@/config'
import { getBaseURL } from '@/core/lib'
import { useAuthStore, useStreamStore } from '@/core/stores'

const SSE_RECONNECT_DELAY = 3000
let alertAudioContext: AudioContext | null = null

export async function armAlertNotifications(): Promise<void> {
  window.localStorage.setItem('siem-alert-sound', 'enabled')
  const AudioContextClass =
    window.AudioContext ??
    (window as typeof window & { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext
  if (AudioContextClass) {
    alertAudioContext ??= new AudioContextClass()
    if (alertAudioContext.state === 'suspended') {
      await alertAudioContext.resume()
    }
  }
  if ('Notification' in window && Notification.permission === 'default') {
    await Notification.requestPermission()
  }
}

export function useLogStream(): void {
  const token = useAuthStore((s) => s.accessToken)
  const setLogConnected = useStreamStore((s) => s.setLogConnected)
  const pushLogEvent = useStreamStore((s) => s.pushLogEvent)
  const sourceRef = useRef<EventSource | null>(null)

  const connect = useCallback(() => {
    if (token === null) return

    const url = `${getBaseURL()}${API_ENDPOINTS.LOGS.STREAM}?token=${encodeURIComponent(token)}`
    const source = new EventSource(url)
    sourceRef.current = source

    source.onopen = () => setLogConnected(true)

    source.addEventListener('log', (event: MessageEvent<string>) => {
      const data = JSON.parse(event.data) as StreamLogEvent
      pushLogEvent({ id: data.id, timestamp: data.timestamp, data })
    })

    source.onerror = () => {
      setLogConnected(false)
      source.close()
      sourceRef.current = null
      setTimeout(connect, SSE_RECONNECT_DELAY)
    }
  }, [token, setLogConnected, pushLogEvent])

  useEffect(() => {
    connect()
    return () => {
      sourceRef.current?.close()
      sourceRef.current = null
      setLogConnected(false)
    }
  }, [connect, setLogConnected])
}

export function useAlertStream(): void {
  const token = useAuthStore((s) => s.accessToken)
  const setAlertConnected = useStreamStore((s) => s.setAlertConnected)
  const pushAlertEvent = useStreamStore((s) => s.pushAlertEvent)
  const sourceRef = useRef<EventSource | null>(null)

  const connect = useCallback(() => {
    if (token === null) return

    const url = `${getBaseURL()}${API_ENDPOINTS.ALERTS.STREAM}?token=${encodeURIComponent(token)}`
    const source = new EventSource(url)
    sourceRef.current = source

    source.onopen = () => setAlertConnected(true)

    source.addEventListener('alert', (event: MessageEvent<string>) => {
      const data = JSON.parse(event.data) as StreamAlertEvent
      void playAlertSound()
      if (
        'Notification' in window &&
        Notification.permission === 'granted' &&
        document.visibilityState !== 'visible'
      ) {
        new Notification(`New ${data.severity ?? 'security'} alert`, {
          body: data.title ?? 'A new SIEM alert requires attention',
          tag: `siem-alert-${data.id}`,
        })
      }
      pushAlertEvent({
        id: data.id,
        timestamp: new Date().toISOString(),
        data,
      })
    })

    source.onerror = () => {
      setAlertConnected(false)
      source.close()
      sourceRef.current = null
      setTimeout(connect, SSE_RECONNECT_DELAY)
    }

  }, [token, setAlertConnected, pushAlertEvent])

  useEffect(() => {
    connect()
    return () => {
      sourceRef.current?.close()
      sourceRef.current = null
      setAlertConnected(false)
    }
  }, [connect, setAlertConnected])
}

async function playAlertSound(): Promise<void> {
  const AudioContextClass =
    window.AudioContext ??
    (window as typeof window & { webkitAudioContext?: typeof AudioContext })
      .webkitAudioContext
  if (!AudioContextClass) {
    console.error('Alert sound is unavailable: Web Audio is not supported')
    return
  }

  try {
    alertAudioContext ??= new AudioContextClass()
    if (alertAudioContext.state === 'suspended') {
      await alertAudioContext.resume()
    }

    const now = alertAudioContext.currentTime
    const gain = alertAudioContext.createGain()
    gain.gain.setValueAtTime(0.0001, now)
    gain.gain.exponentialRampToValueAtTime(0.8, now + 0.025)
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.9)
    gain.connect(alertAudioContext.destination)

    for (const [frequency, offset] of [
      [880, 0],
      [1175, 0.18],
      [880, 0.36],
      [1175, 0.54],
    ] as const) {
      const oscillator = alertAudioContext.createOscillator()
      oscillator.type = 'square'
      oscillator.frequency.setValueAtTime(frequency, now + offset)
      oscillator.connect(gain)
      oscillator.start(now + offset)
      oscillator.stop(now + offset + 0.14)
    }
  } catch (error) {
    console.error('Unable to play alert sound', error)
  }
}
