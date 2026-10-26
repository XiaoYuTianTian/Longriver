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
        <div v-if="searchOpen && needle && hits" class="search-pop">
          <p v-if="hitCount === 0" class="muted">没有匹配。</p>
          <template v-if="hits.people.length">
            <p class="search-label">人物</p>
            <button v-for="person in hits.people" :key="person.id" type="button" @click="openPerson(person.id, person.birth_year)">
              <strong>{{ person.name }}</strong>
              <span>{{ lifeSpan(person.birth_year, person.death_year) }}</span>
            </button>
          </template>
          <template v-if="hits.events.length">
            <p class="search-label">事件</p>
            <button v-for="claim in hits.events" :key="claim.id" type="button" @click="openClaim(claim.id, claim.start_year)">
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
        @polity="openPolity"
        @country="openCountry"
        @place="openPlaceFromMap"
      />
      <aside class="index">
        <header class="index-head">
          <p class="index-year">{{ yearFigures }}</p>
          <p class="index-count">{{ claimCount === 0 ? '这一年还没有记述' : `${claimCount} 条记述` }}</p>
        </header>
        <div class="index-scroll">
          <p v-if="claimCount === 0" class="muted">
            附近有记载的年份：
            <button v-for="near in nearbyYears" :key="near" type="button" class="text-button" @click="setYear(near)">{{ formatYear(near) }}</button>
          </p>
          <button
            v-for="claim in focusedClaims"
            :key="claim.id"
            type="button"
            class="index-row"
            :class="[toneClass(claim), { on: claimOpen(claim.id) }]"
            @click="openClaim(claim.id)"
          >
            <span class="index-title">{{ eventTitle(claim.event_id) || claim.text }}</span>
            <span class="index-meta">{{ claim.time_label }}<template v-if="placeName(claim)">，{{ placeName(claim) }}</template></span>
          </button>
          <button v-if="backgroundClaims.length" type="button" class="text-button wide" @click="showBackground = !showBackground">
            {{ showBackground ? '收起长时段' : `还有 ${backgroundClaims.length} 条跨了多年` }}
          </button>
          <button
            v-for="claim in shownBackground"
            :key="`bg-${claim.id}`"
            type="button"
            class="index-row quiet"
            :class="toneClass(claim)"
            @click="openClaim(claim.id)"
          >
            <span class="index-title">{{ eventTitle(claim.event_id) || claim.text }}</span>
            <span class="index-meta">{{ claim.time_label }}</span>
          </button>
        </div>
        <p class="index-credit">1911 年前的疆域来自 Cliopatria，其后的国界来自 Natural Earth。</p>
      </aside>
      <DetailSheet v-if="sheet" :sheet="sheet" @close="sheet = null" @open="sheet = $event" @look="look" />
      <BookmarkShelf v-if="showBookmarks" @close="showBookmarks = false" @open="openBookmark" />
    </div>

    <Timeline v-show="sheet == null" :year="year" :counts="counts" @change="setYear" />
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
import type { Claim, MapLabel, PlacePoint, Region } from '../lib/types'

const route = useRoute()
const router = useRouter()
const year = ref(1521)
const sheet = ref<Sheet | null>(null)
const query = ref('')
const searchOpen = ref(false)
const showBookmarks = ref(false)
const showBackground = ref(false)
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
  const claim = Number(queryOne(source.claim))
  if (claim) return { kind: 'claim', id: claim }
  const person = Number(queryOne(source.person))
  if (person) return { kind: 'person', id: person }
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
  const current = sheet.value
  if (!current) return next
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

watch([year, sheet], publishQuery, { deep: true })

const yearClaims = computed(() => {
  const pack = data.value
  if (!pack) return []
  return pack.claims.filter((claim) => claimOverlaps(claim, year.value, year.value))
})
const claimCount = computed(() => yearClaims.value.length)
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
  const span = claim.end_year - claim.start_year
  const point = span <= 30 || claim.start_year === year.value ? 0 : 1
  return point * 100000 + toneWeight(claim) * 10000 + span
}

const orderedClaims = computed(() => yearClaims.value.slice().sort((left, right) => rankClaim(left) - rankClaim(right) || left.start_year - right.start_year))
const focusedClaims = computed(() => orderedClaims.value.filter((claim) => rankClaim(claim) < 100000))
const backgroundClaims = computed(() => orderedClaims.value.filter((claim) => rankClaim(claim) >= 100000))
const shownBackground = computed(() => (showBackground.value ? backgroundClaims.value : []))

const nearbyYears = computed(() => {
  const pack = data.value
  if (!pack || claimCount.value > 0) return []
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
  for (const claim of yearClaims.value) {
    const id = claim.region_ids[0]
    if (id == null || seen.has(id)) continue
    seen.add(id)
    const region = pack.regionById.get(id)
    if (!region || region.level === 'region') continue
    if (region.longitude === 0 && region.latitude === 0) continue
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

const activePolity = computed(() => (sheet.value?.kind === 'polity' ? sheet.value.id : null))
const activeCountry = computed(() => (sheet.value?.kind === 'country' ? sheet.value.name : ''))

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

function claimOpen(id: number): boolean {
  return sheet.value?.kind === 'claim' && sheet.value.id === id
}

function toneClass(claim: Claim): string {
  return `tone-${claimTone(claim.text, eventTitle(claim.event_id), claim.topic_slugs)}`
}

function setYear(next: number) {
  showBackground.value = false
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
    openPerson(exact.id, exact.birth_year)
    return
  }
  if (found.people.length === 1 && found.events.length === 0 && found.places.length === 0) {
    openPerson(found.people[0].id, found.people[0].birth_year)
    return
  }
  if (found.events.length === 1 && found.people.length === 0 && found.places.length === 0) {
    openClaim(found.events[0].id, found.events[0].start_year)
    return
  }
  if (found.places.length === 1 && found.people.length === 0 && found.events.length === 0) {
    openPlace(found.places[0].id, placeYear(found.places[0]), true)
  }
}

function openClaim(id: number, nextYear?: number) {
  if (nextYear != null) setYear(nextYear)
  sheet.value = { kind: 'claim', id }
  searchOpen.value = false
  query.value = ''
}

function openPerson(id: number, nextYear: number | null) {
  if (nextYear != null) setYear(nextYear)
  sheet.value = { kind: 'person', id }
  searchOpen.value = false
  query.value = ''
  const regionId = data.value?.personById.get(id)?.region_id
  const region = regionId == null ? null : data.value?.regionById.get(regionId)
  if (region) fly(region.longitude, region.latitude)
}

function openPlace(id: number, nextYear = year.value, shouldFly = false) {
  setYear(nextYear)
  sheet.value = { kind: 'place', id }
  searchOpen.value = false
  query.value = ''
  if (!shouldFly) return
  const region = data.value?.regionById.get(id)
  if (region) fly(region.longitude, region.latitude)
}

function openPlaceFromMap(id: number) {
  const region = data.value?.regionById.get(id)
  sheet.value = { kind: 'place', id }
  if (region) fly(region.longitude, region.latitude)
}

function openPolity(id: number) {
  sheet.value = { kind: 'polity', id }
}

function openCountry(name: string) {
  sheet.value = { kind: 'country', name }
}

function openBookmark(next: Sheet, nextYear: number) {
  setYear(nextYear)
  sheet.value = next
  showBookmarks.value = false
}

function look(target: { year: number; lon: number; lat: number }) {
  setYear(target.year)
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
