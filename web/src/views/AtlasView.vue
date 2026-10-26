<template>
  <section v-if="error" class="page-message">{{ error }}</section>
  <section v-else-if="!data" class="page-message">正在载入知识库</section>
  <section v-else class="desk" :class="{ reading: sheet != null }" @keydown.esc="closeFloats">
    <div class="stage">
    <header class="command">
      <router-link class="brand" to="/">
        <span class="brand-mark">Longriver</span>
        <span class="brand-name">长河</span>
      </router-link>
      <div class="search-wrap">
        <input
          v-model="query"
          class="search"
          type="search"
          placeholder="搜人物、事件、地点"
          @focus="searchOpen = true"
          @input="searchOpen = true"
          @keydown.enter.prevent="openBestHit"
        />
        <Transition name="pop">
        <div v-if="searchOpen && needle && hits" class="search-pop">
          <p v-if="hitCount === 0" class="muted">没有匹配。</p>
          <template v-if="hits.people.length">
            <p class="search-label">人物</p>
            <button v-for="person in hits.people" :key="person.id" type="button" @click="selectPerson(person.id, person.birth_year)">
              <strong>{{ person.name }}</strong>
              <span>{{ lifeSpan(person.birth_year, person.death_year) }}</span>
            </button>
          </template>
          <template v-if="hits.events.length">
            <p class="search-label">事件</p>
            <button v-for="claim in hits.events" :key="claim.id" type="button" @click="selectClaim(claim.id, claim.start_year)">
              <strong>{{ eventTitle(claim.event_id) || claim.text }}</strong>
              <span>{{ claim.time_label }}</span>
            </button>
          </template>
          <template v-if="hits.places.length">
            <p class="search-label">地点</p>
            <button v-for="place in hits.places" :key="place.id" type="button" @click="openPlace(place.id, placeYear(place), true)">
              <strong>{{ place.name }}</strong>
              <span>{{ placeTrail(place) }}</span>
            </button>
          </template>
        </div>
        </Transition>
      </div>
      <label class="year-jump">
        年份
        <input type="number" :min="-3000" :max="2026" :value="year" @change="onYearInput" />
      </label>
      <button type="button" class="text-button shelf-toggle" @click="showBookmarks = !showBookmarks">收藏 {{ bookmarks.length }}</button>
    </header>
      <AtlasMap
        ref="mapRef"
        :year="year"
        :places="places"
        :labels="labels"
        :active-polity="activePolity"
        :active-country="activeCountry"
        :active-place="activePlace"
        :focus-token="focusToken"
        @polity="openPolity"
        @country="openCountry"
        @place="openPlaceFromMap"
      />
      <aside class="index">
        <header class="index-head">
          <p class="index-year">{{ yearFigures }}</p>
          <div class="index-tabs">
            <button type="button" :class="{ on: indexTab === 'events' }" @click="indexTab = 'events'">事件</button>
            <button type="button" :class="{ on: indexTab === 'people' }" @click="indexTab = 'people'">人物</button>
          </div>
          <p class="index-count">{{ indexTab === 'events' ? (eventCount === 0 ? '这一年还没有事件' : `${eventCount} 条事件`) : (personCount === 0 ? '这一年还没有人物' : `${personCount} 位人物`) }}</p>
        </header>
        <div class="index-tags">
          <button type="button" :class="{ on: activeTag === null }" @click="setTag(null)">全部</button>
          <button v-for="tag in visibleTags" :key="tag.slug" type="button" :class="{ on: activeTag === tag.slug }" @click="setTag(tag.slug)">{{ tag.name }}</button>
        </div>
        <div class="index-scroll">
          <p v-if="indexTab === 'events' && eventCount === 0" class="muted">
            附近有记载的年份：
            <button v-for="near in nearbyYears" :key="near" type="button" class="text-button" @click="setYear(near)">{{ formatYear(near) }}</button>
          </p>
          <template v-if="indexTab === 'events'">
            <section v-for="group in claimGroups" :key="group.key">
              <h3 class="index-group">{{ group.name }}</h3>
              <button
                v-for="claim in group.claims"
                :key="claim.id"
                type="button"
                class="index-row"
                :class="[toneClass(claim), { on: selectedClaimId === claim.id }]"
                @click="selectClaim(claim.id)"
              >
                <span class="index-title">{{ eventTitle(claim.event_id) || claim.text }}</span>
                <span class="index-meta">
                  {{ claim.time_label }}<template v-if="placeName(claim)">，{{ placeName(claim) }}</template>
                  <template v-if="!claimMappable(claim)">，图上没有这个点</template>
                </span>
              </button>
            </section>
          </template>
          <template v-else>
            <section v-for="group in personGroups" :key="group.key">
              <h3 class="index-group">{{ group.name }}</h3>
              <button
                v-for="person in group.people"
                :key="person.id"
                type="button"
                class="index-row"
                :class="{ on: selectedPersonId === person.id }"
                @click="selectPerson(person.id)"
              >
                <span class="index-title">{{ person.name }}</span>
                <span class="index-meta">
                  {{ lifeSpan(person.birth_year, person.death_year) || '生卒未收录' }}
                  <template v-if="roleLabel(person.role)">，{{ roleLabel(person.role) }}</template>
                  <template v-if="!personMappable(person)">，图上没有这个点</template>
                </span>
              </button>
            </section>
          </template>
        </div>
        <p class="index-credit">1911 年前的疆域来自 Cliopatria，其后的国界来自 Natural Earth。</p>
      </aside>
      <Transition name="locate">
        <aside v-if="locateTitle && !sheet" class="locate-card">
          <h2>{{ locateTitle }}</h2>
          <p>{{ locateCaption }}</p>
          <button type="button" class="text-button" @click="readSelection">阅读</button>
        </aside>
      </Transition>
      <Transition name="rise">
        <DetailSheet v-if="sheet" :sheet="sheet" @close="sheet = null" @open="openSheet" @look="look" />
      </Transition>
      <Transition name="shelf">
        <BookmarkShelf v-if="showBookmarks" @close="showBookmarks = false" @open="openBookmark" />
      </Transition>
    </div>

    <Transition name="ruler">
      <Timeline v-show="sheet == null" :year="year" :counts="counts" @change="setYear" />
    </Transition>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter, type LocationQuery } from 'vue-router'
import AtlasMap from '../components/AtlasMap.vue'
import BookmarkShelf from '../components/BookmarkShelf.vue'
import DetailSheet, { type Sheet } from '../components/DetailSheet.vue'
import Timeline from '../components/Timeline.vue'
import { bookmarks } from '../lib/bookmarks'
import { decadeCounts } from '../lib/density'
import { HISTORICAL_BORDERS_END, claimOverlaps, claimTone, clampYear, formatYear, lifeSpan } from '../lib/format'
import { ancestors, knowledge, knowledgeError, polityName } from '../lib/knowledge'
import type { Claim, MapLabel, Person, PlacePoint, Region } from '../lib/types'

const route = useRoute()
const router = useRouter()
const year = ref(1521)
const sheet = ref<Sheet | null>(null)
const selectedClaimId = ref<number | null>(null)
const selectedPersonId = ref<number | null>(null)
const indexTab = ref<'events' | 'people'>('events')
const eventTag = ref<string | null>(null)
const personTag = ref<string | null>(null)
const focusToken = ref(0)
const query = ref('')
const searchOpen = ref(false)
const showBookmarks = ref(false)
const mapRef = ref<{ flyTo: (lon: number, lat: number, zoom: number) => void } | null>(null)
let applyingRoute = false

const data = computed(() => knowledge.value)
const error = computed(() => knowledgeError.value)
const needle = computed(() => query.value.trim())
const counts = computed(() => decadeCounts(data.value?.claims ?? []))

function queryOne(value: LocationQuery[string]): string {
  if (Array.isArray(value)) return value[0] ?? ''
  return value == null ? '' : String(value)
}

function sheetFromQuery(source: LocationQuery): Sheet | null {
  const place = Number(queryOne(source.place))
  if (place) return { kind: 'place', id: place }
  const polity = Number(queryOne(source.polity))
  if (polity) return { kind: 'polity', id: polity }
  const country = queryOne(source.country)
  if (country) return { kind: 'country', name: country }
  return null
}

function desiredQuery(): Record<string, string> {
  const next: Record<string, string> = { year: String(year.value) }
  if (selectedClaimId.value != null) {
    next.claim = String(selectedClaimId.value)
    return next
  }
  if (selectedPersonId.value != null) {
    next.person = String(selectedPersonId.value)
    return next
  }
  const current = sheet.value
  if (!current || current.kind === 'claim') return next
  if (current.kind === 'country') next.country = current.name
  else next[current.kind] = String(current.id)
  return next
}

function sameQuery(next: Record<string, string>, source: LocationQuery): boolean {
  const keys = ['year', 'claim', 'person', 'place', 'polity', 'country']
  return keys.every((key) => (next[key] ?? '') === queryOne(source[key]))
}

watch(
  () => route.query,
  (source) => {
    applyingRoute = true
    const rawYear = queryOne(source.year)
    const nextYear = Number(rawYear)
    if (rawYear !== '' && Number.isFinite(nextYear)) year.value = clampYear(nextYear)
    const claim = Number(queryOne(source.claim))
    selectedClaimId.value = claim || null
    const person = Number(queryOne(source.person))
    selectedPersonId.value = claim ? null : person || null
    sheet.value = sheetFromQuery(source)
    applyingRoute = false
  },
  { immediate: true },
)

function publishQuery() {
  if (applyingRoute) return
  const next = desiredQuery()
  if (sameQuery(next, route.query)) return
  void router.replace({ query: next })
}

watch([year, sheet, selectedClaimId, selectedPersonId], publishQuery, { deep: true })

watch([year, data], () => {
  if (applyingRoute) return
  const pack = data.value
  if (!pack) return
  const id = selectedClaimId.value
  if (id != null) {
    const claim = pack.claims.find((item) => item.id === id)
    if (!claim || !claimOverlaps(claim, year.value, year.value)) {
      if (sheet.value?.kind === 'claim' && sheet.value.id === id) sheet.value = null
      selectedClaimId.value = null
    }
  }
  const personId = selectedPersonId.value
  if (personId != null) {
    const person = pack.personById.get(personId)
    if (!person || !personInYear(person, year.value)) {
      if (sheet.value?.kind === 'person' && sheet.value.id === personId) sheet.value = null
      selectedPersonId.value = null
    }
  }
})

watch(selectedClaimId, (id) => {
  if (id != null) focusToken.value += 1
}, { immediate: true })

watch(selectedPersonId, (id) => {
  if (id != null) focusToken.value += 1
}, { immediate: true })

const roleNames: Record<string, string> = {
  scientist: '科学家',
  politician: '政治家',
  writer: '文学家',
  artist: '艺术家',
  military: '军事',
  religious: '宗教',
  explorer: '探险',
  other: '其他',
}

const yearClaims = computed(() => {
  const pack = data.value
  if (!pack) return []
  return pack.claims.filter((claim) => claimOverlaps(claim, year.value, year.value))
})
const yearFigures = computed(() => {
  if (year.value > 0) return String(year.value)
  if (year.value === 0) return '前1'
  return `前${-year.value}`
})

function eventTitle(eventId: number | null): string {
  if (eventId == null) return ''
  return data.value?.eventById.get(eventId)?.title ?? ''
}

function toneWeight(claim: Claim): number {
  const tone = claimTone(claim.text, eventTitle(claim.event_id), claim.topic_slugs)
  if (tone === 'war' || tone === 'treaty' || tone === 'reign' || tone === 'politics') return 0
  if (tone === 'birth') return 3
  if (tone === 'culture') return 2
  return 1
}

function rankClaim(claim: Claim): number {
  return toneWeight(claim) * 10000 + (claim.end_year - claim.start_year)
}

function isBirthClaim(claim: Claim): boolean {
  if (claim.topic_slugs.includes('birth')) return true
  return eventTitle(claim.event_id).endsWith('出生')
}

function personInYear(person: Person, at: number): boolean {
  if (person.birth_year == null) return false
  if (person.death_year == null) return person.birth_year === at
  return person.birth_year <= at && at <= person.death_year
}

function roleLabel(role: string | undefined): string {
  return roleNames[role || 'other'] || '其他'
}

function topicLabel(slug: string): string {
  return data.value?.topics.find((topic) => topic.slug === slug)?.name || slug
}

function hasPoint(region: Region): boolean {
  return Number.isFinite(region.longitude) && Number.isFinite(region.latitude) && !(region.longitude === 0 && region.latitude === 0)
}

function claimRegion(claim: Claim): Region | null {
  const pack = data.value
  if (!pack) return null
  const regions = claim.region_ids.flatMap((id) => {
    const region = pack.regionById.get(id)
    return region ? [region] : []
  })
  return regions.find(hasPoint) ?? regions[0] ?? null
}

function claimMappable(claim: Claim): boolean {
  const region = claimRegion(claim)
  return region != null && hasPoint(region)
}

function polityIdAt(region: Region, at: number): number | null {
  let best: number[] | null = null
  for (const span of region.polity_spans) {
    if (span.length < 3 || span[0] > at || at > span[1]) continue
    if (!best || span[1] - span[0] < best[1] - best[0]) best = span
  }
  return best ? best[2] : null
}

const yearEvents = computed(() => yearClaims.value.filter((claim) => !isBirthClaim(claim)))
const eventCount = computed(() => yearEvents.value.length)
const filteredEvents = computed(() => {
  const tag = eventTag.value
  if (!tag || !yearEvents.value.some((claim) => claim.topic_slugs.includes(tag))) return yearEvents.value
  return yearEvents.value.filter((claim) => claim.topic_slugs.includes(tag))
})
const eventTags = computed(() => {
  const slugs = new Set<string>()
  for (const claim of yearEvents.value) {
    for (const slug of claim.topic_slugs) slugs.add(slug)
  }
  return [...slugs].map((slug) => ({ slug, name: topicLabel(slug) }))
})

const yearPeople = computed(() => {
  const pack = data.value
  if (!pack) return []
  return pack.people.filter((person) => personInYear(person, year.value))
})
const personCount = computed(() => yearPeople.value.length)
const filteredPeople = computed(() => {
  const tag = personTag.value
  const people = yearPeople.value
  if (!tag || !people.some((person) => (person.role || 'other') === tag)) return people
  return people.filter((person) => (person.role || 'other') === tag)
})
const personTags = computed(() => {
  const slugs = new Set<string>()
  for (const person of yearPeople.value) slugs.add(person.role || 'other')
  return [...slugs].map((slug) => ({ slug, name: roleLabel(slug) }))
})
const visibleTags = computed(() => (indexTab.value === 'events' ? eventTags.value : personTags.value))
const activeTag = computed(() => (indexTab.value === 'events' ? eventTag.value : personTag.value))

function setTag(slug: string | null) {
  if (indexTab.value === 'events') eventTag.value = slug
  else personTag.value = slug
}

const claimGroups = computed(() => {
  const pack = data.value
  if (!pack) return []
  const buckets = new Map<string, { key: string; name: string; lon: number; claims: Claim[] }>()
  for (const claim of filteredEvents.value) {
    const region = claimRegion(claim)
    const chain = region ? ancestors(region, pack.regionById) : []
    const country = [...chain].reverse().find((item) => item.level === 'country') ?? chain[chain.length - 2] ?? region
    const key = country ? String(country.id) : 'none'
    const lon = country && hasPoint(country) ? country.longitude : region && hasPoint(region) ? region.longitude : 1000
    const bucket = buckets.get(key) ?? { key, name: country?.name ?? '地点未标出', lon, claims: [] }
    bucket.claims.push(claim)
    bucket.lon = Math.min(bucket.lon, lon)
    buckets.set(key, bucket)
  }
  return [...buckets.values()]
    .map((group) => ({
      ...group,
      claims: group.claims.slice().sort((left, right) => rankClaim(left) - rankClaim(right) || left.start_year - right.start_year),
    }))
    .sort((left, right) => left.lon - right.lon || left.name.localeCompare(right.name, 'zh'))
})

const personGroups = computed(() => {
  const pack = data.value
  if (!pack) return []
  const buckets = new Map<string, { key: string; name: string; lon: number; people: Person[] }>()
  for (const person of filteredPeople.value) {
    const region = person.region_id == null ? null : pack.regionById.get(person.region_id) ?? null
    const chain = region ? ancestors(region, pack.regionById) : []
    const country = [...chain].reverse().find((item) => item.level === 'country') ?? chain[chain.length - 2] ?? region
    const key = country ? String(country.id) : 'none'
    const lon = country && hasPoint(country) ? country.longitude : region && hasPoint(region) ? region.longitude : 1000
    const bucket = buckets.get(key) ?? { key, name: country?.name ?? '地点未标出', lon, people: [] }
    bucket.people.push(person)
    bucket.lon = Math.min(bucket.lon, lon)
    buckets.set(key, bucket)
  }
  return [...buckets.values()]
    .map((group) => ({
      ...group,
      people: group.people.slice().sort((left, right) => left.name.localeCompare(right.name, 'zh')),
    }))
    .sort((left, right) => left.lon - right.lon || left.name.localeCompare(right.name, 'zh'))
})

const selectedClaim = computed(() => {
  const id = selectedClaimId.value
  const pack = data.value
  if (id == null || !pack) return null
  return pack.claims.find((claim) => claim.id === id) ?? null
})
const selectedPerson = computed(() => {
  const id = selectedPersonId.value
  const pack = data.value
  if (id == null || !pack) return null
  return pack.personById.get(id) ?? null
})
const selectedRegion = computed(() => {
  const pack = data.value
  if (selectedPerson.value?.region_id != null && pack) return pack.regionById.get(selectedPerson.value.region_id) ?? null
  return selectedClaim.value ? claimRegion(selectedClaim.value) : null
})
const selectedPlace = computed(() => {
  const region = selectedRegion.value
  if (!region || !hasPoint(region)) return null
  return region
})
const selectedPolityId = computed(() => {
  const region = selectedRegion.value
  if (!region || year.value > HISTORICAL_BORDERS_END) return null
  return polityIdAt(region, year.value)
})
const selectedPolityTitle = computed(() => {
  const pack = data.value
  if (!pack) return ''
  const id = selectedPolityId.value
  if (id == null) {
    if (year.value <= HISTORICAL_BORDERS_END || !selectedRegion.value) return ''
    const chain = ancestors(selectedRegion.value, pack.regionById)
    return [...chain].reverse().find((item) => item.level === 'country')?.name ?? ''
  }
  const polity = pack.polityById.get(id)
  return polity ? polityName(polity) : ''
})
const activePlace = computed(() => {
  const region = selectedPlace.value
  if (!region) return null
  return { id: region.id, name: region.name, lon: region.longitude, lat: region.latitude }
})
const locateTitle = computed(() => {
  if (selectedClaim.value) return eventTitle(selectedClaim.value.event_id) || selectedClaim.value.text
  return selectedPerson.value?.name || ''
})
const locateCaption = computed(() => {
  const parts: string[] = []
  if (selectedPerson.value && !selectedClaim.value) {
    const role = roleLabel(selectedPerson.value.role)
    if (role) parts.push(role)
  }
  if (selectedPlace.value) parts.push(selectedPlace.value.name)
  if (selectedPolityTitle.value) parts.push(selectedPolityTitle.value)
  if (!selectedPlace.value) parts.push('图上没有这个点')
  return parts.length ? `${parts.join('，')}。` : ''
})

const nearbyYears = computed(() => {
  const pack = data.value
  if (!pack || eventCount.value > 0) return []
  let before = Number.NEGATIVE_INFINITY
  let after = Number.POSITIVE_INFINITY
  for (const claim of pack.claims) {
    if (claim.end_year < year.value) before = Math.max(before, claim.end_year)
    if (claim.start_year > year.value) after = Math.min(after, claim.start_year)
  }
  return [before, after].filter((value) => Number.isFinite(value))
})

const places = computed<PlacePoint[]>(() => {
  const pack = data.value
  if (!pack) return []
  const points: PlacePoint[] = []
  const seen = new Set<number>()
  const regions = indexTab.value === 'people'
    ? yearPeople.value.flatMap((person) => {
      const region = person.region_id == null ? null : pack.regionById.get(person.region_id)
      return region ? [region] : []
    })
    : yearEvents.value.flatMap((claim) => {
      const region = claimRegion(claim)
      return region ? [region] : []
    })
  for (const region of regions) {
    if (seen.has(region.id) || region.level === 'region') continue
    if (region.longitude === 0 && region.latitude === 0) continue
    seen.add(region.id)
    points.push({ id: region.id, name: region.name, lon: region.longitude, lat: region.latitude })
  }
  return points
})

const labels = computed<MapLabel[]>(() => {
  const pack = data.value
  if (!pack) return []
  if (year.value > HISTORICAL_BORDERS_END) {
    return [...pack.countryLabels]
      .filter((row) => row.n)
      .sort((left, right) => right.a - left.a)
      .slice(0, 18)
      .map((row) => ({ key: `c-${row.n}`, kind: 'country' as const, name: row.n, lon: row.lon, lat: row.lat }))
  }
  return pack.polities
    .flatMap((polity) => {
      const label = polity.labels.find((item) => item[0] <= year.value && year.value <= item[1])
      if (!label) return []
      return [{
        key: `p-${polity.id}`,
        kind: 'polity' as const,
        id: polity.id,
        name: polityName(polity),
        lon: label[2],
        lat: label[3],
        area: label[4],
      }]
    })
    .sort((left, right) => right.area - left.area)
    .slice(0, 18)
})

const hits = computed(() => {
  const pack = data.value
  const q = needle.value
  if (!pack || !q) return null
  const people = pack.people
    .filter((person) => person.name.includes(q) || (person.description ?? '').includes(q))
    .sort((left, right) => Number(right.name.startsWith(q)) - Number(left.name.startsWith(q)) || left.name.localeCompare(right.name, 'zh'))
    .slice(0, 6)
  const events = pack.claims
    .filter((claim) => {
      const title = claim.event_id == null ? '' : pack.eventById.get(claim.event_id)?.title ?? ''
      return `${claim.text} ${title}`.includes(q)
    })
    .slice(0, 6)
  const foundPlaces = pack.regions
    .filter((region) => region.level !== 'region' && (region.name.includes(q) || (region.description ?? '').includes(q)))
    .slice(0, 6)
  return { people, events, places: foundPlaces }
})
const hitCount = computed(() => (hits.value ? hits.value.people.length + hits.value.events.length + hits.value.places.length : 0))

const activePolity = computed(() => (sheet.value?.kind === 'polity' ? sheet.value.id : selectedPolityId.value))
const activeCountry = computed(() => {
  if (sheet.value?.kind === 'country') return sheet.value.name
  if (year.value <= HISTORICAL_BORDERS_END) return ''
  const pack = data.value
  const region = selectedRegion.value
  if (!pack || !region) return ''
  const chain = ancestors(region, pack.regionById)
  const country = [...chain].reverse().find((item) => item.level === 'country')
  if (!country) return ''
  return pack.countryLabels.some((row) => row.n === country.name) ? country.name : ''
})

function placeName(claim: Claim): string {
  const id = claim.region_ids[0]
  if (id == null) return ''
  return data.value?.regionById.get(id)?.name ?? ''
}

function placeTrail(region: Region): string {
  const pack = data.value
  if (!pack) return ''
  return ancestors(region, pack.regionById).slice(0, -1).map((item) => item.name).join(' / ')
}

function placeYear(region: Region): number {
  const span = region.polity_spans.find((item) => item.length >= 2)
  return span ? clampYear(span[0]) : year.value
}

function toneClass(claim: Claim): string {
  return `tone-${claimTone(claim.text, eventTitle(claim.event_id), claim.topic_slugs)}`
}

function setYear(next: number) {
  year.value = clampYear(next)
}

function onYearInput(event: Event) {
  setYear(Number((event.target as HTMLInputElement).value))
}

function fly(lon: number, lat: number) {
  if (!Number.isFinite(lon) || !Number.isFinite(lat)) return
  if (lon === 0 && lat === 0) return
  mapRef.value?.flyTo(lon, lat, 3.4)
}

function openBestHit() {
  const found = hits.value
  if (!found) return
  const exact = found.people.find((person) => person.name === needle.value)
  if (exact) {
    selectPerson(exact.id, exact.birth_year)
    return
  }
  if (found.people.length === 1 && found.events.length === 0 && found.places.length === 0) {
    selectPerson(found.people[0].id, found.people[0].birth_year)
    return
  }
  if (found.events.length === 1 && found.people.length === 0 && found.places.length === 0) {
    selectClaim(found.events[0].id, found.events[0].start_year)
    return
  }
  if (found.places.length === 1 && found.people.length === 0 && found.events.length === 0) {
    openPlace(found.places[0].id, placeYear(found.places[0]), true)
  }
}

function personMappable(person: Person): boolean {
  const region = person.region_id == null ? null : data.value?.regionById.get(person.region_id)
  return region != null && hasPoint(region)
}

function selectClaim(id: number, nextYear?: number) {
  if (nextYear != null) setYear(nextYear)
  const same = selectedClaimId.value === id
  selectedPersonId.value = null
  selectedClaimId.value = id
  if (sheet.value?.kind === 'claim' || sheet.value?.kind === 'person') sheet.value = null
  searchOpen.value = false
  query.value = ''
  if (same) focusToken.value += 1
}

function selectPerson(id: number, nextYear?: number | null) {
  if (nextYear != null) setYear(nextYear)
  const same = selectedPersonId.value === id
  selectedClaimId.value = null
  selectedPersonId.value = id
  if (sheet.value?.kind === 'claim' || sheet.value?.kind === 'person') sheet.value = null
  searchOpen.value = false
  query.value = ''
  if (same) focusToken.value += 1
}

function readClaim() {
  if (selectedClaimId.value == null) return
  sheet.value = { kind: 'claim', id: selectedClaimId.value }
}

function readPerson() {
  if (selectedPersonId.value == null) return
  sheet.value = { kind: 'person', id: selectedPersonId.value }
}

function readSelection() {
  if (selectedClaimId.value != null) readClaim()
  else readPerson()
}

function openSheet(next: Sheet) {
  if (next.kind === 'claim') {
    selectClaim(next.id)
    readClaim()
    return
  }
  if (next.kind === 'person') {
    selectPerson(next.id)
    readPerson()
    return
  }
  selectedClaimId.value = null
  selectedPersonId.value = null
  sheet.value = next
}

function openPlace(id: number, nextYear = year.value, shouldFly = false) {
  setYear(nextYear)
  selectedClaimId.value = null
  selectedPersonId.value = null
  sheet.value = { kind: 'place', id }
  searchOpen.value = false
  query.value = ''
  if (!shouldFly) return
  const region = data.value?.regionById.get(id)
  if (region) fly(region.longitude, region.latitude)
}

function openPlaceFromMap(id: number) {
  const region = data.value?.regionById.get(id)
  selectedClaimId.value = null
  selectedPersonId.value = null
  sheet.value = { kind: 'place', id }
  if (region) fly(region.longitude, region.latitude)
}

function openPolity(id: number) {
  selectedClaimId.value = null
  selectedPersonId.value = null
  sheet.value = { kind: 'polity', id }
}

function openCountry(name: string) {
  selectedClaimId.value = null
  selectedPersonId.value = null
  sheet.value = { kind: 'country', name }
}

function openBookmark(next: Sheet, nextYear: number) {
  setYear(nextYear)
  showBookmarks.value = false
  if (next.kind === 'claim') {
    selectClaim(next.id)
    readClaim()
    return
  }
  if (next.kind === 'person') {
    selectPerson(next.id)
    readPerson()
    return
  }
  selectedClaimId.value = null
  selectedPersonId.value = null
  sheet.value = next
}

function look(target: { year: number; lon: number; lat: number }) {
  const claim = selectedClaim.value
  const person = selectedPerson.value
  const keepYear = (claim != null && claimOverlaps(claim, year.value, year.value))
    || (person != null && personInYear(person, year.value))
  sheet.value = null
  if (!keepYear) setYear(target.year)
  fly(target.lon, target.lat)
}

function closeFloats() {
  searchOpen.value = false
  if (showBookmarks.value) showBookmarks.value = false
  else sheet.value = null
}

function onWindowKey(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  if (target?.closest('input, textarea')) return
  if (event.key === 'Escape') {
    closeFloats()
    return
  }
  if (target?.closest('.timeline')) return
  const step = event.altKey ? 100 : event.shiftKey ? 10 : 1
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault()
    setYear(year.value + (event.key === 'ArrowRight' ? step : -step))
  }
}

function onPointerDown(event: PointerEvent) {
  const target = event.target as HTMLElement | null
  if (!target?.closest('.search-wrap')) searchOpen.value = false
}

onMounted(() => {
  publishQuery()
  window.addEventListener('keydown', onWindowKey)
  window.addEventListener('pointerdown', onPointerDown)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onWindowKey)
  window.removeEventListener('pointerdown', onPointerDown)
})
</script>
