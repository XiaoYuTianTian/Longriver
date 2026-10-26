export interface Citation {
  id: number
  source_title: string
  edition_label: string
  locator: string
  quotation: string
  stable_url: string
}

export interface Claim {
  id: number
  text: string
  brief: string
  certainty: string
  time_label: string
  start_year: number
  end_year: number
  region_ids: number[]
  topic_slugs: string[]
  event_id: number | null
  snapshot_id: number | null
  citations: Citation[]
}

export interface Region {
  id: number
  slug: string
  name: string
  sort_order: number
  parent_id: number | null
  latitude: number
  longitude: number
  level: string
  polity_spans: number[][]
  description: string
  image: string
  image_credit: string
}

export interface Topic {
  slug: string
  name: string
}

export interface EventRow {
  id: number
  title: string
  time_label: string
  person_ids: number[]
}

export interface Snapshot {
  id: number
  label: string
  time_label: string
}

export interface Person {
  id: number
  name: string
  birth_year: number | null
  death_year: number | null
  description: string
  region_id: number | null
  image: string
  image_credit: string
  wikidata: string
  role?: string
}

export interface Polity {
  id: number
  name: string
  zh: string
  capital: string
  wikipedia: string
  from: number
  to: number
  labels: number[][]
}

export interface CountryLabel {
  n: string
  lon: number
  lat: number
  a: number
}

export interface KnowledgePackage {
  version: number
  full: boolean
  claims: Claim[]
  regions: Region[]
  topics: Topic[]
  events: EventRow[]
  snapshots: Snapshot[]
  people: Person[]
}

export type BookmarkKind = 'claim' | 'person' | 'place' | 'polity'

export interface Bookmark {
  id: string
  kind: BookmarkKind
  targetId: number
  note: string
  updatedAt: number
}

export interface MapLabel {
  key: string
  kind: 'polity' | 'country'
  id?: number
  name: string
  lon: number
  lat: number
}

export interface PlacePoint {
  id: number
  name: string
  lon: number
  lat: number
}
