import { TIMELINE_END, TIMELINE_START, clampYear } from './format'
import type { Claim } from './types'

export const DECADE = 10

export function decadeIndex(year: number): number {
  return Math.floor((clampYear(year) - TIMELINE_START) / DECADE)
}

export function decadeCounts(claims: Claim[]): Uint32Array {
  const size = decadeIndex(TIMELINE_END) + 1
  const bins = new Uint32Array(size)
  for (const claim of claims) {
    const index = decadeIndex(claim.start_year)
    if (index >= 0 && index < bins.length) bins[index] += 1
  }
  return bins
}
