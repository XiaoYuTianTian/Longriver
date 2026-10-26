import type { Claim } from './types'

function archiveRank(claim: Claim): number {
  if (claim.text.includes('出生')) return 2
  if (claim.topic_slugs.some((slug) => slug === 'politics' || slug === 'culture' || slug === 'technology')) return 0
  return 1
}

function yearGap(left: Claim, right: Claim): number {
  if (left.end_year >= right.start_year && right.end_year >= left.start_year) return 0
  return left.end_year < right.start_year ? right.start_year - left.end_year : left.start_year - right.end_year
}

export function samePlaceClaims(current: Claim, claims: Claim[], limit = 6): Claim[] {
  const regions = new Set(current.region_ids)
  if (regions.size === 0) return []
  return claims
    .filter((claim) => claim.id !== current.id && claim.region_ids.some((id) => regions.has(id)))
    .filter((claim) => yearGap(current, claim) <= 30)
    .sort(
      (left, right) =>
        yearGap(current, left) - yearGap(current, right) ||
        left.end_year - left.start_year - (right.end_year - right.start_year) ||
        archiveRank(left) - archiveRank(right) ||
        left.start_year - right.start_year ||
        left.id - right.id,
    )
    .slice(0, limit)
}

export function contemporaryClaims(current: Claim, claims: Claim[], limit = 4): Claim[] {
  const regions = new Set(current.region_ids)
  return claims
    .filter((claim) => claim.id !== current.id && claim.start_year <= current.end_year && claim.end_year >= current.start_year)
    .filter((claim) => !claim.region_ids.some((id) => regions.has(id)))
    .sort((left, right) => {
      const span = (claim: Claim) => claim.end_year - claim.start_year
      const near = (claim: Claim) => (span(claim) <= 40 ? 0 : 1)
      return (
        near(left) - near(right) ||
        archiveRank(left) - archiveRank(right) ||
        Math.abs(left.start_year - current.start_year) - Math.abs(right.start_year - current.start_year) ||
        span(left) - span(right) ||
        left.id - right.id
      )
    })
    .slice(0, limit)
}
