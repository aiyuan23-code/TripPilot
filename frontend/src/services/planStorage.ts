import type { TripPlan } from '@/types'

const STORAGE_KEY = 'trippilot.latest-plan'

export function saveTripPlan(plan: TripPlan): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(plan))
}

export function loadTripPlan(): TripPlan | null {
  const value = sessionStorage.getItem(STORAGE_KEY)
  if (!value) return null

  try {
    const parsed: unknown = JSON.parse(value)
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      'city' in parsed &&
      'days' in parsed &&
      Array.isArray(parsed.days)
    ) {
      return parsed as TripPlan
    }
  } catch {
    sessionStorage.removeItem(STORAGE_KEY)
  }
  return null
}

