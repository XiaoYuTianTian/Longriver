import { shallowRef } from 'vue'
import { hasHan } from './format'
import type {
  Claim,
  CountryLabel,
  EventRow,
  KnowledgePackage,
  Person,
  Polity,
  Region,
  Snapshot,
} from './types'

export interface IndexedKnowledge {
  version: number
  claims: Claim[]
  regions: Region[]
  events: EventRow[]
  people: Person[]
  polities: Polity[]
  countryLabels: CountryLabel[]
  regionById: Map<number, Region>
  personById: Map<number, Person>
  eventById: Map<number, EventRow>
  snapshotById: Map<number, Snapshot>
  polityById: Map<number, Polity>
  claimsByPerson: Map<number, number[]>
}

export const knowledge = shallowRef<IndexedKnowledge | null>(null)
export const knowledgeError = shallowRef('')

let loading: Promise<IndexedKnowledge> | null = null

function indexPackage(
  pack: KnowledgePackage,
  polities: Polity[],
  countryLabels: CountryLabel[],
): IndexedKnowledge {
  const regionById = new Map(pack.regions.map((region) => [region.id, region]))
  const personById = new Map(pack.people.map((person) => [person.id, person]))
  const eventById = new Map(pack.events.map((event) => [event.id, event]))
  const snapshotById = new Map(pack.snapshots.map((snapshot) => [snapshot.id, snapshot]))
  const polityById = new Map(polities.map((polity) => [polity.id, polity]))
  const claimsByEvent = new Map<number, number[]>()
  for (const claim of pack.claims) {
    if (claim.event_id == null) continue
    const list = claimsByEvent.get(claim.event_id)
    if (list) list.push(claim.id)
    else claimsByEvent.set(claim.event_id, [claim.id])
  }
  const claimsByPerson = new Map<number, number[]>()
  for (const event of pack.events) {
    const claimIds = claimsByEvent.get(event.id) ?? []
    for (const personId of event.person_ids) {
      const existing = claimsByPerson.get(personId)
      if (existing) existing.push(...claimIds)
      else claimsByPerson.set(personId, [...claimIds])
    }
  }
  return {
    version: pack.version,
    claims: pack.claims,
    regions: pack.regions,
    events: pack.events,
    people: pack.people,
    polities,
    countryLabels,
    regionById,
    personById,
    eventById,
    snapshotById,
    polityById,
    claimsByPerson,
  }
}

async function readJson<T>(url: string): Promise<T> {
  const response = await fetch(url)
  if (!response.ok) throw new Error(`无法读取 ${url}`)
  return response.json() as Promise<T>
}

export function ensureKnowledge(): Promise<IndexedKnowledge> {
  if (knowledge.value) return Promise.resolve(knowledge.value)
  if (!loading) {
    loading = Promise.all([
      readJson<KnowledgePackage>('/knowledge-package.json'),
      readJson<{ polities: Polity[] }>('/polities.json'),
      readJson<CountryLabel[]>('/country-labels.json'),
    ])
      .then(([pack, polityIndex, countryLabels]) => {
        const indexed = indexPackage(pack, polityIndex.polities, countryLabels)
        knowledge.value = indexed
        return indexed
      })
      .catch((error: unknown) => {
        loading = null
        knowledgeError.value = error instanceof Error ? error.message : '知识包没有载入'
        throw error
      })
  }
  return loading
}

export function polityName(polity: Polity): string {
  return hasHan(polity.zh) ? polity.zh : polity.name
}

export function ancestors(region: Region, byId: Map<number, Region>): Region[] {
  const chain: Region[] = []
  let current: Region | undefined = region
  const seen = new Set<number>()
  while (current && !seen.has(current.id)) {
    seen.add(current.id)
    chain.unshift(current)
    current = current.parent_id == null ? undefined : byId.get(current.parent_id)
  }
  return chain
}
