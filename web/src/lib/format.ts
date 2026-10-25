import type { Claim, Person } from './types'

export const TIMELINE_START = -3000
export const TIMELINE_END = 2026
export const HISTORICAL_BORDERS_END = 1911
export const BORDER_START = -3000
export const BUCKET_YEARS = 100

export interface Era {
  name: string
  start: number
  end: number
}

export const chinaEras: Era[] = [
  { name: '夏', start: -2070, end: -1600 },
  { name: '商', start: -1600, end: -1046 },
  { name: '西周', start: -1046, end: -771 },
  { name: '春秋', start: -770, end: -476 },
  { name: '战国', start: -475, end: -221 },
  { name: '秦', start: -221, end: -207 },
  { name: '西汉', start: -202, end: 8 },
  { name: '新', start: 9, end: 23 },
  { name: '东汉', start: 25, end: 220 },
  { name: '三国', start: 220, end: 280 },
  { name: '西晋', start: 266, end: 316 },
  { name: '东晋', start: 317, end: 420 },
  { name: '南北朝', start: 420, end: 589 },
  { name: '隋', start: 581, end: 618 },
  { name: '唐', start: 618, end: 907 },
  { name: '五代', start: 907, end: 979 },
  { name: '北宋', start: 960, end: 1127 },
  { name: '南宋', start: 1127, end: 1279 },
  { name: '元', start: 1271, end: 1368 },
  { name: '明', start: 1368, end: 1644 },
  { name: '清', start: 1644, end: 1911 },
  { name: '中华民国', start: 1912, end: 1949 },
  { name: '中华人民共和国', start: 1949, end: TIMELINE_END },
]

export const worldEras: Era[] = [
  { name: '青铜时代', start: -3000, end: -1200 },
  { name: '铁器时代', start: -1200, end: -500 },
  { name: '古典时代', start: -500, end: 500 },
  { name: '中世纪', start: 500, end: 1450 },
  { name: '近代早期', start: 1450, end: 1800 },
  { name: '近代', start: 1800, end: 1900 },
  { name: '现代', start: 1900, end: TIMELINE_END },
]

export function formatYear(year: number): string {
  if (year > 0) return `${year}年`
  if (year === 0) return '公元前1年'
  return `公元前${-year}年`
}

export function formatSpan(start: number, end: number): string {
  return start === end ? formatYear(start) : `${formatYear(start)} – ${formatYear(end)}`
}

export function lifeSpan(birth: number | null, death: number | null): string | null {
  if (birth == null && death == null) return null
  if (death == null) return `${formatYear(birth as number)}生 · 卒年未收录`
  if (birth == null) return `卒于${formatYear(death)}`
  return `${formatYear(birth)} – ${formatYear(death)}`
}

export function overlaps(start: number, end: number, spanStart: number, spanEnd: number): boolean {
  return start <= spanEnd && end >= spanStart
}

export function personVisible(person: Person, start: number, end: number): boolean {
  if (person.birth_year == null) return false
  if (person.death_year == null) return person.birth_year >= start && person.birth_year <= end
  return person.birth_year <= end && person.death_year >= start
}

export function claimOverlaps(claim: Claim, start: number, end: number): boolean {
  return overlaps(start, end, claim.start_year, claim.end_year)
}

export function certaintyLabel(value: string): string {
  if (value === 'verified') return '已证实'
  if (value === 'inferred') return '学界推断'
  if (value === 'disputed') return '存在争议'
  if (value === 'unverified') return '待核查'
  return value
}

export interface BriefBlock {
  heading: string
  text: string
}

export function parseBrief(brief: string): BriefBlock[] {
  if (!brief.trim()) return []
  return brief.split('\n\n').flatMap((raw) => {
    const block = raw.trim()
    if (!block) return []
    const lines = block.split('\n')
    if (lines[0].startsWith('§')) {
      const text = lines.slice(1).join('\n').trim()
      return text ? [{ heading: lines[0].slice(1).trim(), text }] : []
    }
    return [{ heading: '', text: block }]
  })
}

const WAR = /战争|战役|围城|叛乱|起义|革命|内战/
const TREATY = /条约|会议|公约|宣言|和约/
const REIGN = /即位|登基|年间|称帝|开国/

export function claimTone(text: string, title: string, topics: string[]): string {
  const label = `${title} ${text}`
  if (label.includes('出生')) return 'birth'
  if (WAR.test(label)) return 'war'
  if (TREATY.test(label)) return 'treaty'
  if (REIGN.test(label)) return 'reign'
  if (topics.includes('culture')) return 'culture'
  if (topics.includes('technology')) return 'tech'
  if (topics.includes('economy')) return 'economy'
  if (topics.includes('politics')) return 'politics'
  return 'society'
}

export function briefExcerpt(brief: string, limit = 88): string {
  const text = parseBrief(brief).map((block) => block.text).join(' ').replace(/\s+/g, ' ').trim()
  if (!text) return ''
  return text.length > limit ? `${text.slice(0, limit)}…` : text
}

export function tidyCredit(credit: string): string {
  return credit.replace(/(.{3,}?)\1+/g, '$1').replace(/\s+/g, ' ').trim()
}

export function clampYear(year: number): number {
  if (!Number.isFinite(year)) return 1521
  return Math.min(TIMELINE_END, Math.max(TIMELINE_START, Math.round(year)))
}

export function mediaSrc(path: string): string {
  const trimmed = path.trim().replace(/^\/+/, '')
  if (!trimmed) return ''
  return trimmed.startsWith('media/') ? `/${trimmed}` : `/media/${trimmed}`
}

export function bucketFor(year: number): number {
  const clamped = Math.min(year, HISTORICAL_BORDERS_END)
  return Math.max(0, Math.floor((clamped - BORDER_START) / BUCKET_YEARS))
}

const HAN = /[\u4e00-\u9fff]/

export function hasHan(value: string): boolean {
  return HAN.test(value)
}
