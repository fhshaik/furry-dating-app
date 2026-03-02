export interface NotificationItem {
  id: number
  type: string
  payload: Record<string, unknown> | null
  is_read: boolean
  created_at: string
}

export interface NotificationsListResponse {
  items: NotificationItem[]
  page: number
  limit: number
  total: number
  has_more: boolean
}

function getNumericPayloadValue(
  payload: Record<string, unknown> | null,
  key: string,
): number | null {
  const value = payload?.[key]
  return typeof value === 'number' ? value : null
}

function humanizeNotificationType(type: string): string {
  return type
    .split('_')
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(' ')
}

export function getNotificationTitle(type: string): string {
  switch (type) {
    case 'message_received':
      return 'New message'
    case 'match_created':
      return 'New match'
    case 'pack_join_request_received':
      return 'Pack join request'
    case 'pack_join_request_approved':
      return 'Pack request approved'
    case 'pack_join_request_rejected':
      return 'Pack request declined'
    default:
      return humanizeNotificationType(type)
  }
}

export function getNotificationDescription(
  type: string,
  payload: Record<string, unknown> | null,
): string {
  const suffix =
    payload && typeof payload === 'object'
      ? Object.entries(payload)
          .filter(([, value]) => typeof value === 'string' || typeof value === 'number')
          .slice(0, 2)
          .map(([key, value]) => `${key.replace(/_/g, ' ')}: ${value}`)
          .join(' • ')
      : ''

  switch (type) {
    case 'message_received':
      return suffix || 'Someone sent you a new message.'
    case 'match_created':
      return suffix || 'A new mutual match is ready to chat.'
    case 'pack_join_request_received':
      return suffix || 'A pack has a new join request waiting for review.'
    case 'pack_join_request_approved':
      return suffix || 'Your pack join request was approved.'
    case 'pack_join_request_rejected':
      return suffix || 'Your pack join request was declined.'
    default:
      return suffix || 'There is a new update waiting for you.'
  }
}

export function formatNotificationDate(isoString: string): string {
  return new Date(isoString).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function getNotificationHref(notification: NotificationItem): string | null {
  switch (notification.type) {
    case 'message_received': {
      const conversationId = getNumericPayloadValue(notification.payload, 'conversation_id')
      return conversationId == null ? null : `/inbox/${conversationId}`
    }
    case 'match_created': {
      const matchId = getNumericPayloadValue(notification.payload, 'match_id')
      return matchId == null ? null : `/matches#match-${matchId}`
    }
    case 'pack_join_request_received':
    case 'pack_join_request_approved':
    case 'pack_join_request_rejected': {
      const packId = getNumericPayloadValue(notification.payload, 'pack_id')
      return packId == null ? null : `/packs/${packId}`
    }
    default:
      return null
  }
}
