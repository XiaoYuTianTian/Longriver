<template>
  <section v-if="!data" class="page-message">正在载入知识库</section>
  <article v-else-if="!claim" class="page-message">这条陈述不在知识包中。</article>
  <article v-else class="detail">
    <p class="actions"><button type="button" class="text-button" @click="back">返回</button></p>
    <p class="kicker">{{ claim.time_label }}<template v-if="place"> · {{ place.name }}</template></p>
      <h1>{{ title || claim.text }}</h1>
    <p v-if="snapshot" class="muted">{{ snapshot }}</p>
    <p class="lead">{{ claim.text }}</p>
    <section v-for="(block, index) in brief" :key="index">
      <h2 v-if="block.heading">{{ block.heading }}</h2>
      <p>{{ block.text }}</p>
    </section>
    <p v-if="brief.length" class="muted">正文摘自维基百科，CC BY-SA 4.0</p>

    <section v-if="samePlace.length">
      <h2>同地</h2>
      <router-link v-for="row in samePlace" :key="row.id" class="card link-card" :to="`/claims/${row.id}`">
        <span class="kicker">{{ row.time_label }}</span>
        <strong>{{ labelOf(row) }}</strong>
        <span class="fact">{{ row.text }}</span>
      </router-link>
    </section>
    <section v-if="contemporary.length">
      <h2>同时代</h2>
      <router-link v-for="row in contemporary" :key="row.id" class="card link-card" :to="`/claims/${row.id}`">
        <span class="kicker">{{ row.time_label }}</span>
        <strong>{{ labelOf(row) }}</strong>
        <span class="fact">{{ row.text }}</span>
      </router-link>
    </section>

    <section v-if="people.length">
      <h2>相关人物</h2>
      <router-link v-for="person in people" :key="person.id" class="card link-card" :to="`/people/${person.id}`">
        <img v-if="person.image && !failed.has(person.id)" :src="mediaSrc(person.image)" :alt="person.name" @error="failed.add(person.id)" />
        <strong>{{ person.name }}</strong>
        <span class="muted">{{ lifeSpan(person.birth_year, person.death_year) || '查看人物' }}</span>
        <span v-if="person.image_credit" class="muted">头像：{{ tidyCredit(person.image_credit) }}</span>
      </router-link>
    </section>

    <p v-if="claim.certainty !== 'unverified'" class="muted">{{ certaintyLabel(claim.certainty) }}</p>
    <section>
      <h2>出处</h2>
      <p v-for="citation in claim.citations" :key="citation.id" class="muted">
        {{ citationText(citation) }}
        <a v-if="citation.stable_url" :href="citation.stable_url" target="_blank" rel="noreferrer">{{ citation.stable_url }}</a>
      </p>
    </section>
    <p class="actions">
      <BookmarkButton kind="claim" :target-id="claim.id" />
      <router-link v-if="place" :to="{ path: '/', query: { year: String(claim.start_year), place: String(place.id) } }">在地图上看</router-link>
    </p>
  </article>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'
import BookmarkButton from '../components/BookmarkButton.vue'
import { certaintyLabel, lifeSpan, mediaSrc, parseBrief, tidyCredit } from '../lib/format'
import { knowledge } from '../lib/knowledge'
import { contemporaryClaims, samePlaceClaims } from '../lib/reading'
import type { Citation, Claim } from '../lib/types'

const props = defineProps<{ id: string }>()
const router = useRouter()
const data = computed(() => knowledge.value)
const failed = reactive(new Set<number>())
const claim = computed(() => data.value?.claims.find((row) => row.id === Number(props.id)) ?? null)
const title = computed(() => {
  const eventId = claim.value?.event_id
  if (eventId == null) return ''
  return data.value?.eventById.get(eventId)?.title ?? ''
})
const snapshot = computed(() => {
  const snapshotId = claim.value?.snapshot_id
  if (snapshotId == null) return ''
  return data.value?.snapshotById.get(snapshotId)?.label ?? ''
})
const place = computed(() => {
  const placeId = claim.value?.region_ids[0]
  if (placeId == null) return null
  return data.value?.regionById.get(placeId) ?? null
})
const brief = computed(() => parseBrief(claim.value?.brief ?? ''))
const people = computed(() => {
  const eventId = claim.value?.event_id
  const pack = data.value
  if (eventId == null || !pack) return []
  const ids = pack.eventById.get(eventId)?.person_ids ?? []
  return ids.flatMap((id) => {
    const person = pack.personById.get(id)
    return person ? [person] : []
  })
})
const samePlace = computed(() => (claim.value && data.value ? samePlaceClaims(claim.value, data.value.claims) : []))
const contemporary = computed(() => (claim.value && data.value ? contemporaryClaims(claim.value, data.value.claims) : []))

function back() {
  if (window.history.length > 1) router.back()
  else void router.push('/')
}

function labelOf(row: Claim): string {
  const eventTitle = row.event_id == null ? '' : data.value?.eventById.get(row.event_id)?.title ?? ''
  return eventTitle || row.text
}

function citationText(citation: Citation): string {
  return [citation.source_title, citation.edition_label, citation.locator].filter((part) => part && part !== '维基百科条目' && part !== '条目正文').join(' · ')
}
</script>
