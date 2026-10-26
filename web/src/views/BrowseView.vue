<template>
  <section v-if="!data" class="page-message">正在载入知识库</section>
  <section v-else class="browse">
    <header class="browse-head">
      <h1>浏览</h1>
      <p class="muted">按时代、人物、事件或地点往下读。打开地图时会带上对应年份。</p>
      <input v-model="query" class="search" type="search" placeholder="人名、事件、地点或时代" />
      <div class="chips">
        <button type="button" :class="{ on: section === 'era' }" @click="section = 'era'">时代</button>
        <button type="button" :class="{ on: section === 'world' }" @click="section = 'world'">世界</button>
        <button type="button" :class="{ on: section === 'person' }" @click="section = 'person'">人物</button>
        <button type="button" :class="{ on: section === 'event' }" @click="section = 'event'">事件</button>
        <button type="button" :class="{ on: section === 'place' }" @click="section = 'place'">地点</button>
      </div>
    </header>

    <p v-if="(section === 'era' || section === 'world') && needle && visibleEras.length === 0" class="muted">
      没有这个时代。下面是名称里带「{{ needle }}」的人物和事件。
    </p>
    <div v-if="(section === 'era' || section === 'world') && needle && visibleEras.length === 0" class="stack">
      <router-link v-for="person in people.slice(0, 5)" :key="person.id" class="card link-card" :to="`/people/${person.id}`">
        <strong>{{ person.name }}</strong>
        <span class="muted">{{ lifeSpan(person.birth_year, person.death_year) || '人物' }}</span>
      </router-link>
      <article v-for="claim in events.slice(0, 5)" :key="claim.id" class="card entry" :class="toneClass(claim)">
        <router-link :to="`/claims/${claim.id}`">
          <span class="kicker">{{ claimLine(claim) }}</span>
          <strong>{{ eventTitle(claim.event_id) || claim.text }}</strong>
        </router-link>
      </article>
    </div>
    <div v-if="section === 'era' || section === 'world'" class="era-grid">
      <article v-for="era in visibleEras" :key="era.name" class="card era-card">
        <p class="kicker">{{ formatSpan(era.start, era.end) }}</p>
        <h2>{{ era.name }}</h2>
        <p class="era-stats">
          <span>{{ eraCounts(era).claims }} 条记述</span>
          <span>{{ eraCounts(era).people }} 位人物</span>
        </p>
        <p class="actions">
          <router-link :to="{ path: '/', query: { year: String(era.start) } }">在地图上看</router-link>
          <button type="button" class="quiet-link" @click="showPeople(era)">这个时代的人</button>
        </p>
      </article>
    </div>

    <div v-else-if="section === 'person'" class="stack">
      <p v-if="eraLimit" class="actions">
        <button type="button" class="text-button" @click="eraLimit = null">显示全部人物，不限{{ eraLimit.name }}</button>
      </p>
      <p v-if="!needle && !eraLimit" class="muted">人物很多。输入姓名，或从上面的时代点「这个时代的人」。</p>
      <p v-if="(needle || eraLimit) && visiblePeople.length === 0" class="muted">没有匹配的人物。</p>
      <router-link v-for="person in visiblePeople" :key="person.id" class="card link-card" :to="`/people/${person.id}`">
        <strong>{{ person.name }}</strong>
        <span class="muted">{{ lifeSpan(person.birth_year, person.death_year) || '人物' }}</span>
        <span v-if="person.description" class="fact">{{ person.description }}</span>
      </router-link>
      <button v-if="needle && people.length > limit" type="button" class="text-button" @click="limit += 60">再显示一些</button>
    </div>

    <div v-else-if="section === 'event'" class="stack">
      <label class="year-jump">
        没有关键词时，按年份看
        <input v-model.number="browseYear" type="number" min="-3000" max="2026" />
      </label>
      <p v-if="visibleEvents.length === 0" class="muted">没有匹配的事件。</p>
      <article v-for="claim in visibleEvents" :key="claim.id" class="card entry" :class="toneClass(claim)">
        <router-link :to="`/claims/${claim.id}`">
          <span class="kicker">{{ claimLine(claim) }}</span>
          <strong>{{ eventTitle(claim.event_id) || claim.text }}</strong>
        </router-link>
        <p class="fact">{{ claim.text }}</p>
        <router-link v-if="claim.region_ids[0]" :to="mapLink(claim)">在地图上看</router-link>
      </article>
      <button v-if="events.length > limit" type="button" class="text-button" @click="limit += 40">再显示一些</button>
    </div>

    <div v-else class="stack">
      <p v-if="!needle" class="muted">先显示记述较多的地点。输入地名可以查全部。</p>
      <p v-if="visiblePlaces.length === 0" class="muted">没有匹配的地点。</p>
      <article v-for="place in visiblePlaces" :key="place.id" class="card">
        <router-link :to="`/places/${place.id}`">
          <strong>{{ place.name }}</strong>
          <span class="muted">{{ trail(place) }} · {{ placeClaimCount(place.id) }} 条</span>
        </router-link>
        <router-link :to="{ path: '/', query: { place: String(place.id), year: String(placeYear(place)) } }">在地图上看</router-link>
      </article>
      <button v-if="placePool.length > limit" type="button" class="text-button" @click="limit += 40">再显示一些</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { chinaEras, claimOverlaps, claimTone, clampYear, formatSpan, lifeSpan, personVisible, worldEras, type Era } from '../lib/format'
import { ancestors, knowledge } from '../lib/knowledge'
import type { Claim, Region } from '../lib/types'

const data = computed(() => knowledge.value)
const section = ref<'era' | 'world' | 'person' | 'event' | 'place'>('era')
const query = ref('')
const limit = ref(40)
const eraLimit = ref<Era | null>(null)
const browseYear = ref(1521)
const needle = computed(() => query.value.trim())

watch([section, query], () => {
  limit.value = 60
})

const visibleEras = computed(() => {
  const rows = section.value === 'world' ? worldEras : chinaEras
  if (!needle.value) return rows
  return rows.filter((era) => era.name.includes(needle.value))
})

function eraCounts(era: Era): { claims: number; people: number } {
  const pack = data.value
  if (!pack) return { claims: 0, people: 0 }
  return {
    claims: pack.claims.filter((claim) => claimOverlaps(claim, era.start, era.end)).length,
    people: pack.people.filter((person) => personVisible(person, era.start, era.end)).length,
  }
}

const people = computed(() => {
  const pack = data.value
  if (!pack) return []
  const pool = eraLimit.value
    ? pack.people.filter((person) => personVisible(person, eraLimit.value!.start, eraLimit.value!.end))
    : pack.people
  return pool
    .filter((person) => !needle.value || person.name.includes(needle.value) || (person.description ?? '').includes(needle.value))
    .slice()
    .sort((left, right) => (left.birth_year ?? 99999) - (right.birth_year ?? 99999) || left.name.localeCompare(right.name, 'zh'))
})

const visiblePeople = computed(() => (needle.value || eraLimit.value ? people.value.slice(0, limit.value) : []))

const events = computed(() => {
  const pack = data.value
  if (!pack) return []
  const year = clampYear(browseYear.value)
  return pack.claims
    .filter((claim) => {
      const title = claim.event_id == null ? '' : pack.eventById.get(claim.event_id)?.title ?? ''
      const place = claim.region_ids[0] == null ? '' : pack.regionById.get(claim.region_ids[0])?.name ?? ''
      if (!needle.value) return claimOverlaps(claim, year, year)
      return `${claim.text} ${title} ${place} ${claim.brief}`.includes(needle.value)
    })
    .sort((left, right) => {
      const span = (claim: Claim) => claim.end_year - claim.start_year
      const point = (claim: Claim) => (span(claim) <= 30 || claim.start_year === year ? 0 : 1)
      return point(left) - point(right) || span(left) - span(right) || left.start_year - right.start_year
    })
})

const visibleEvents = computed(() => events.value.slice(0, limit.value))

const placePool = computed(() => {
  const pack = data.value
  if (!pack) return []
  const rows = pack.regions.filter((region) => region.level !== 'region' && (!needle.value || region.name.includes(needle.value) || (region.description ?? '').includes(needle.value)))
  if (needle.value) return rows.slice().sort((left, right) => left.sort_order - right.sort_order)
  return rows
    .filter((region) => (claimTotals.value.get(region.id) ?? 0) > 0)
    .sort((left, right) => (claimTotals.value.get(right.id) ?? 0) - (claimTotals.value.get(left.id) ?? 0))
})

const visiblePlaces = computed(() => placePool.value.slice(0, limit.value))

function showPeople(era: Era) {
  eraLimit.value = era
  section.value = 'person'
}

function eventTitle(eventId: number | null): string {
  if (eventId == null) return ''
  return data.value?.eventById.get(eventId)?.title ?? ''
}

function toneClass(claim: Claim): string {
  return `tone-${claimTone(claim.text, eventTitle(claim.event_id), claim.topic_slugs)}`
}

function placeYear(place: Region): number {
  const span = place.polity_spans.find((item) => item.length >= 2)
  if (!span) return 1521
  return clampYear(span[0])
}

function claimLine(claim: Claim): string {
  const place = claim.region_ids[0] == null ? undefined : data.value?.regionById.get(claim.region_ids[0])
  return [claim.time_label, place?.name].filter(Boolean).join(' · ')
}

function mapLink(claim: Claim) {
  const place = claim.region_ids[0]
  return { path: '/', query: { year: String(claim.start_year), place: place == null ? undefined : String(place) } }
}

function trail(place: Region): string {
  const pack = data.value
  if (!pack) return ''
  const names = ancestors(place, pack.regionById).slice(0, -1).map((item) => item.name)
  return names.join(' / ') || '世界'
}

const claimTotals = computed(() => {
  const totals = new Map<number, number>()
  for (const claim of data.value?.claims ?? []) {
    for (const id of claim.region_ids) totals.set(id, (totals.get(id) ?? 0) + 1)
  }
  return totals
})

function placeClaimCount(id: number): number {
  return claimTotals.value.get(id) ?? 0
}
</script>
