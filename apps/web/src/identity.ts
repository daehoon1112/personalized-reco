/** 데모 아이덴티티 — userId(localStorage, 유저 스위처로 변경) + sessionId(sessionStorage).
 *
 * 유저를 바꾸면 세션도 새로 판다 — 세션은 한 유저의 연속 행동 단위라서다
 * (silver 세션화·attribution이 session_id 기준).
 */

import type { TrackerIdentity } from './tracker'

const USER_KEY = 'reco.userId'
const CONSENT_KEY = 'reco.consent'
const SESSION_KEY = 'reco.sessionId'

export function loadIdentity(fallbackUserId: string): TrackerIdentity {
  const userId = localStorage.getItem(USER_KEY) ?? fallbackUserId
  let sessionId = sessionStorage.getItem(SESSION_KEY)
  if (!sessionId) {
    sessionId = crypto.randomUUID()
    sessionStorage.setItem(SESSION_KEY, sessionId)
  }
  return {
    userId,
    sessionId,
    consent: localStorage.getItem(CONSENT_KEY) !== 'false',
  }
}

export function switchUser(userId: string): TrackerIdentity {
  localStorage.setItem(USER_KEY, userId)
  const sessionId = crypto.randomUUID()
  sessionStorage.setItem(SESSION_KEY, sessionId)
  return { userId, sessionId, consent: localStorage.getItem(CONSENT_KEY) !== 'false' }
}

export function setConsent(identity: TrackerIdentity, consent: boolean): TrackerIdentity {
  localStorage.setItem(CONSENT_KEY, String(consent))
  return { ...identity, consent }
}
