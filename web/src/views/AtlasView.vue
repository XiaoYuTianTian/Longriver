<template>
  <section v-if="error" class="page-message">{{ error }}</section>
  <section v-else-if="!data" class="page-message">正在载入知识库</section>
  <section v-else class="atlas">
    <AtlasMap
      ref="mapRef"
      :year="year"
      :places="places"
      :labels="labels"
      :active-polity="polityId"
      :active-country="country"
      @polity="openPolity"
      @country="openCountry"
      @place="openPlace"
    />
    <aside class="panel">
      <div class="year-tools">
        <YearBar :year="year" @change="setYear" />
        <label class="year-jump">
          跳到
          <input type="number" :min="-3000" :max="2026" :value="year" @change="onYearInput" />
        </label>
      </div>
      <div class="era-jumps">
        <button v-for="era in jumpYears" :key="era.name" type="button" @click="setYear(era.year)">{{ era.name }}</button>
      </div>
      <p class="year-summary">{{ formatYear(year) }} · {{ claimCount }} 条记述</p>
      <p class="muted attribution">疆域 Cliopatria CC BY 4.0 · 陆地与 1912 年后国界 Natural Earth</p>

      <article v-if="polity" class="card focus-card tone-reign">
        <h2>{{ polityTitle }}</h2>
        <p v-if="polity.capital" class="muted">都城 {{ polity.capital }}</p>
        <p class="muted">{{ formatSpan(polity.from, polity.to) }}</p>
        <p v-if="polityLatin" class="muted">{{ polityLatin }}</p>
        <p class="actions">
          <BookmarkButton kind="polity" :target-id="polity.id" />
          <a v-if="polity.wikipedia" :href="wikipediaHref(polity.wikipedia)" target="_blank" rel="noreferrer">维基百科</a>
        </p>
      </article>

      <article v-else-if="place" class="card focus-card tone-treaty">
        <h2>{{ place.name }}</h2>
        <p class="muted">{{ placeTrail }}</p>
        <p v-if="place.description" class="fact">{{ briefExcerpt(place.description, 120) }}</p>
        <p class="actions">
          <BookmarkButton kind="place" :target-id="place.id" />
          <router-link :to="`/places/${place.id}`">地点档案</router-link>
        </p>
      </article>

      <article v-else-if="country" class="card focus-card tone-politics">
        <h2>{{ country }}</h2>
        <p class="muted">1912 年以后的国界。</p>
      </article>

      <h3>这一年发生的</h3>
      <ul class="tone-legend">
        <li class="tone-war">战争</li>
        <li class="tone-treaty">会议条约</li>
        <li class="tone-reign">在位</li>
        <li class="tone-birth">出生</li>
      </ul>
      <p v-if="claimCount === 0" class="muted">
        这一年还没有收录。
        <button v-for="near in nearbyYears" :key="near" type="button" class="text-button" @click="setYear(near)">{{ formatYear(near) }}</button>
      </p>
      <router-link
        v-for="claim in focusedClaims"
        :key="claim.id"
        class="card link-card"
        :class="toneClass(claim)"
        :to="`/claims/${claim.id}`"
      >
        <span class="kicker">{{ claim.time_label }}<template v-if="placeName(claim)"> · {{ placeName(claim) }}</template></span>
        <strong>{{ eventTitle(claim.event_id) || claim.text }}</strong>
        <span v-if="claim.text && claim.text !== eventTitle(claim.event_id)" class="fact">{{ claim.text }}</span>
        <span v-if="excerpt(claim)" class="excerpt">{{ excerpt(claim) }}</span>
      </router-link>
      <button v-if="backgroundClaims.length" type="button" class="text-button wide" @click="showBackground = !showBackground">
        {{ showBackground ? '收起' : '仍在进行的长时段' }} · {{ backgroundClaims.length }}
      </button>
      <router-link
        v-for="claim in shownBackground"
        :key="`bg-${claim.id}`"
        class="card link-card quiet"
        :class="toneClass(claim)"
        :to="`/claims/${claim.id}`"
      >
        <span class="kicker">{{ claim.time_label }}<template v-if="placeName(claim)"> · {{ placeName(claim) }}</template></span>
        <strong>{{ eventTitle(claim.event_id) || claim.text }}</strong>
        <span class="fact">{{ claim.text }}</span>
      </router-link>
    </aside>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AtlasMap from '../components/AtlasMap.vue'
import BookmarkButton from '../components/BookmarkButton.vue'
import YearBar from '../components/YearBar.vue'
import { HISTORICAL_BORDERS_END, briefExcerpt, claimOverlaps, claimTone, clampYear, formatSpan, formatYear } from '../lib/format'
import { ancestors, knowledge, knowledgeError, polityName } from '../lib/knowledge'
import type { Claim, MapLabel, PlacePoint } from '../lib/types'

const route = useRoute()
const router = useRouter()
const year = ref(1521)
const polityId = ref<number | null>(null)
const placeId = ref<number | null>(null)
const country = ref('')
const showBackground = ref(false)
const mapRef = ref<{ flyTo: (lon: number, lat: number, zoom: number) => void } | null>(null)
const jumpYears = [
  { name: '战国', year: -300 },
  { name: '唐', year: 750 },
  { name: '宋', year: 1100 },
  { name: '明', year: 1521 },
  { name: '清', year: 1750 },
  { name: '1912', year: 1912 },
  { name: '1949', year: 1949 },
]

const data = computed(() => knowledge.value)
const error = computed(() => knowledgeError.value)

watch(
  () => route.query.year,
  (value) => {
    const next = Number(value)
    if (Number.isFinite(next)) year.value = next
  },
  { immediate: true },
)

watch(year, (value) => {
  if (String(route.query.year ?? '') === String(value)) return
  void router.replace({ query: { ...route.query, year: String(value) } })
})

const yearClaims = computed(() => {
  const pack = data.value
  if (!pack) return []
  return pack.claims.filter((claim) => claimOverlaps(claim, year.value, year.value))
})

const claimCount = computed(() => yearClaims.value.length)

function rankClaim(claim: Claim): number {
  const span = claim.end_year - claim.start_year
  const point = span <= 30 || claim.start_year === year.value ? 0 : 1
  return point * 100000 + span
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

const polity = computed(() => (polityId.value == null ? null : data.value?.polityById.get(polityId.value) ?? null))
const place = computed(() => (placeId.value == null ? null : data.value?.regionById.get(placeId.value) ?? null))
const polityTitle = computed(() => (polity.value ? polityName(polity.value) : ''))
const polityLatin = computed(() => {
  const row = polity.value
  if (!row || !row.name || row.name === polityTitle.value) return ''
  return row.name
})
const placeTrail = computed(() => {
  const row = place.value
  const pack = data.value
  if (!row || !pack) return ''
  return ancestors(row, pack.regionById).map((item) => item.name).join(' · ')
})

function eventTitle(eventId: number | null): string {
  if (eventId == null) return ''
  return data.value?.eventById.get(eventId)?.title ?? ''
}

function placeName(claim: Claim): string {
  const id = claim.region_ids[0]
  if (id == null) return ''
  return data.value?.regionById.get(id)?.name ?? ''
}

function excerpt(claim: Claim): string {
  const text = briefExcerpt(claim.brief)
  if (!text || text === claim.text) return ''
  return text
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

function openPolity(id: number) {
  polityId.value = id
  placeId.value = null
  country.value = ''
}

function openCountry(name: string) {
  country.value = name
  polityId.value = null
  placeId.value = null
}

function openPlace(id: number) {
  placeId.value = id
  polityId.value = null
  country.value = ''
  const region = data.value?.regionById.get(id)
  if (region) mapRef.value?.flyTo(region.longitude, region.latitude, 3.4)
}

function wikipediaHref(title: string): string {
  if (title.startsWith('http')) return title
  return `https://en.wikipedia.org/wiki/${encodeURIComponent(title.replaceAll(' ', '_'))}`
}

watch(
  () => route.query.place,
  (value) => {
    const id = Number(value)
    if (Number.isFinite(id) && id) openPlace(id)
  },
  { immediate: true },
)
</script>
