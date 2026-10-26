<template>
  <section class="sheet" :class="{ tall }">
    <div class="sheet-handle" @pointerdown="onHandle">
      <button type="button" class="text-button" @click="tall = !tall">{{ tall ? '收起' : '展开' }}</button>
      <button type="button" class="text-button" @click="emit('close')">关闭</button>
    </div>

    <div v-if="!data" class="sheet-body">正在载入知识库</div>
    <div v-else-if="sheet.kind === 'claim'" class="sheet-body">
      <article v-if="claim" class="reading" :class="claimToneClass">
        <DetailCanvas
          :title="claimTitle || claim.text"
          :year="claim.time_label"
          :place="claimPlace?.name || ''"
          :sentence="claimLead || claim.text"
          :band="bandColor"
          :image="artUrl"
          :note="artNote"
        />
        <p class="actions">
          <BookmarkButton kind="claim" :target-id="claim.id" />
          <button v-if="claimPlace" type="button" class="text-button" @click="lookClaim">在地图上定位</button>
        </p>
        <details class="source-fold">
          <summary>原文</summary>
          <p v-if="!claimBrief.length" class="muted">知识包里这条只有一句话。</p>
          <section v-for="(block, index) in claimBrief" :key="index">
            <h3 v-if="block.heading">{{ block.heading }}</h3>
            <p>{{ block.text }}</p>
          </section>
          <p v-if="claimBrief.length" class="muted">正文摘自维基百科，CC BY-SA 4.0</p>
          <h3>出处</h3>
          <p v-for="citation in claim.citations" :key="citation.id" class="muted">
            <a v-if="citation.stable_url" :href="citation.stable_url" target="_blank" rel="noreferrer">{{ citationLabel(citation) || '维基百科' }}</a>
            <template v-else>{{ citationLabel(citation) }}</template>
          </p>
        </details>
      </article>
      <p v-else class="muted">这条记述不在知识包中。</p>
      <section v-if="samePlace.length">
        <h3>同地</h3>
        <button v-for="row in samePlace" :key="row.id" type="button" class="card link-card" @click="emit('open', { kind: 'claim', id: row.id })">
          <span class="kicker">{{ row.time_label }}</span>
          <strong>{{ labelOf(row) }}</strong>
          <span class="fact">{{ row.text }}</span>
        </button>
      </section>
      <section v-if="contemporary.length">
        <h3>同时代</h3>
        <button v-for="row in contemporary" :key="row.id" type="button" class="card link-card" @click="emit('open', { kind: 'claim', id: row.id })">
          <span class="kicker">{{ row.time_label }}</span>
          <strong>{{ labelOf(row) }}</strong>
          <span class="fact">{{ row.text }}</span>
        </button>
      </section>
      <section v-if="claimPeople.length">
        <h3>相关人物</h3>
        <button v-for="person in claimPeople" :key="person.id" type="button" class="card link-card" @click="emit('open', { kind: 'person', id: person.id })">
          <img v-if="person.image && !failed.has(person.id)" :src="mediaSrc(person.image)" :alt="person.name" @error="failed.add(person.id)" />
          <strong>{{ person.name }}</strong>
          <span class="muted">{{ lifeSpan(person.birth_year, person.death_year) || '查看人物' }}</span>
        </button>
      </section>
    </div>

    <div v-else-if="sheet.kind === 'person'" class="sheet-body">
      <article v-if="person" class="reading">
        <DetailCanvas
          :title="person.name"
          :year="lifeSpan(person.birth_year, person.death_year) || '生卒未收录'"
          :place="personPlace?.name || roleName(person.role)"
          :sentence="person.description || person.name"
          band="#1f4e5f"
          :image="personFailed ? null : artUrl"
          :note="artNote"
        />
        <p class="actions">
          <BookmarkButton kind="person" :target-id="person.id" />
          <button v-if="personPlace" type="button" class="text-button" @click="lookPerson">在地图上定位</button>
        </p>
        <details v-if="person.description" class="source-fold">
          <summary>原文</summary>
          <p>{{ person.description }}</p>
        </details>
      </article>
      <p v-else class="muted">这位人物不在知识包中。</p>
      <h3>相关记述</h3>
      <p v-if="personClaims.length === 0" class="muted">没有关联记述。</p>
      <button v-for="row in personClaims" :key="row.id" type="button" class="card link-card" @click="emit('open', { kind: 'claim', id: row.id })">
        <span class="kicker">{{ row.time_label }}</span>
        <strong>{{ row.text }}</strong>
      </button>
    </div>

    <div v-else-if="sheet.kind === 'place'" class="sheet-body">
      <article v-if="place" class="reading">
        <DetailCanvas
          :title="place.name"
          year=""
          :place="placeTrail"
          :sentence="place.description || place.name"
          band="#8a6232"
          :image="placeFailed ? null : artUrl"
          :note="artNote"
        />
        <p class="actions">
          <BookmarkButton kind="place" :target-id="place.id" />
          <button type="button" class="text-button" @click="lookPlace">在地图上定位</button>
        </p>
      </article>
      <p v-else class="muted">这个地点不在知识包中。</p>
      <h3>记述</h3>
      <button v-for="row in placeClaims" :key="row.id" type="button" class="card link-card" @click="emit('open', { kind: 'claim', id: row.id })">
        <span class="kicker">{{ row.time_label }}</span>
        <strong>{{ row.text }}</strong>
      </button>
    </div>

    <div v-else-if="sheet.kind === 'polity'" class="sheet-body">
      <article v-if="polity" class="reading tone-reign">
        <DetailCanvas
          :title="polityTitle"
          :year="formatSpan(polity.from, polity.to)"
          :place="polity.capital ? `都城 ${polity.capital}` : ''"
          :sentence="polityLatin || polityTitle"
          band="#8c4a32"
        />
        <p class="actions">
          <BookmarkButton kind="polity" :target-id="polity.id" />
          <a v-if="polity.wikipedia" :href="wikipediaHref(polity.wikipedia)" target="_blank" rel="noreferrer">维基百科</a>
        </p>
      </article>
      <p v-else class="muted">这个政权不在知识包中。</p>
    </div>

    <div v-else-if="sheet.kind === 'country'" class="sheet-body">
      <article class="reading tone-politics">
        <DetailCanvas :title="sheet.name" year="1912 年以后" place="" sentence="这一年的国界。" band="#1f4e5f" />
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import BookmarkButton from './BookmarkButton.vue'
import DetailCanvas from './DetailCanvas.vue'
import { claimTone, clampYear, formatSpan, lifeSpan, mediaSrc, parseBrief, tidyCredit } from '../lib/format'
import { ancestors, knowledge, polityName } from '../lib/knowledge'
import { contemporaryClaims, samePlaceClaims } from '../lib/reading'
import type { Citation, Claim } from '../lib/types'

export type Sheet =
  | { kind: 'claim'; id: number }
  | { kind: 'person'; id: number }
  | { kind: 'place'; id: number }
  | { kind: 'polity'; id: number }
  | { kind: 'country'; name: string }

const props = defineProps<{ sheet: Sheet }>()
const emit = defineEmits<{
  close: []
  open: [sheet: Sheet]
  look: [target: { year: number; lon: number; lat: number }]
}>()

const tall = ref(false)
const failed = reactive(new Set<number>())
const personFailed = ref(false)
const placeFailed = ref(false)
const artUrl = ref<string | null>(null)
const artNote = ref('')
const data = computed(() => knowledge.value)
const bands: Record<string, string> = {
  war: '#c45a32',
  treaty: '#2f6f9a',
  reign: '#8c4a32',
  birth: '#8a8178',
  culture: '#6b5a2e',
  tech: '#3e8a58',
  economy: '#a24e7a',
  politics: '#1f4e5f',
  society: '#4a5f9a',
}
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

function roleName(role: string | undefined): string {
  if (!role) return ''
  return roleNames[role] || ''
}

let artToken = 0
let artObjectUrl = ''

function releaseArt() {
  if (artObjectUrl) URL.revokeObjectURL(artObjectUrl)
  artObjectUrl = ''
  artUrl.value = null
  artNote.value = ''
}

async function loadArt(token: number) {
  await new Promise((resolve) => window.setTimeout(resolve, 280))
  if (token !== artToken) return
  const sheet = props.sheet
  const pack = data.value
  if (!pack) return
  if (sheet.kind === 'person') {
    const row = pack.personById.get(sheet.id)
    if (!row || token !== artToken) return
    if (row.image) {
      artUrl.value = mediaSrc(row.image)
      artNote.value = row.image_credit ? tidyCredit(row.image_credit) : ''
      return
    }
  }
  if (sheet.kind === 'place') {
    const row = pack.regionById.get(sheet.id)
    if (!row?.image || token !== artToken) return
    artUrl.value = mediaSrc(row.image)
    artNote.value = row.image_credit ? tidyCredit(row.image_credit) : ''
    return
  }
  if (sheet.kind !== 'claim' && sheet.kind !== 'person') return
  try {
    const response = await fetch(`/detail-art/${sheet.kind}/${sheet.id}.webp`)
    if (token !== artToken || !response.ok) return
    const blob = await response.blob()
    if (token !== artToken) return
    releaseArt()
    artObjectUrl = URL.createObjectURL(blob)
    artUrl.value = artObjectUrl
    artNote.value = '示意，不是史料'
  } catch {
    if (token === artToken) artNote.value = ''
  }
}

watch(() => props.sheet, () => {
  tall.value = false
  personFailed.value = false
  placeFailed.value = false
  releaseArt()
  artToken += 1
  void loadArt(artToken)
}, { immediate: true })

onBeforeUnmount(() => {
  artToken += 1
  releaseArt()
})

const claim = computed(() => {
  const sheet = props.sheet
  if (sheet.kind !== 'claim' || !data.value) return null
  return data.value.claims.find((row) => row.id === sheet.id) ?? null
})
const claimTitle = computed(() => {
  const eventId = claim.value?.event_id
  if (eventId == null) return ''
  return data.value?.eventById.get(eventId)?.title ?? ''
})
const claimToneClass = computed(() => (claim.value ? `tone-${claimTone(claim.value.text, claimTitle.value, claim.value.topic_slugs)}` : ''))
const bandColor = computed(() => {
  const row = claim.value
  if (!row) return '#1f4e5f'
  const tone = claimTone(row.text, claimTitle.value, row.topic_slugs)
  return bands[tone] || '#1f4e5f'
})
const claimLead = computed(() => {
  const row = claim.value
  if (!row) return ''
  const text = row.text.trim()
  const heading = claimTitle.value || text
  const body = text.replace(/^[^，]{0,40}，\s*/, '').replace(/。$/, '')
  if (!text || text === heading || body === heading) return ''
  return text
})
const claimBrief = computed(() => parseBrief(claim.value?.brief ?? ''))
const claimPlace = computed(() => {
  const id = claim.value?.region_ids[0]
  if (id == null) return null
  return data.value?.regionById.get(id) ?? null
})
const samePlace = computed(() => (claim.value && data.value ? samePlaceClaims(claim.value, data.value.claims) : []))
const contemporary = computed(() => (claim.value && data.value ? contemporaryClaims(claim.value, data.value.claims) : []))
const claimPeople = computed(() => {
  const eventId = claim.value?.event_id
  const pack = data.value
  if (eventId == null || !pack) return []
  const ids = pack.eventById.get(eventId)?.person_ids ?? []
  return ids.flatMap((id) => {
    const person = pack.personById.get(id)
    return person ? [person] : []
  })
})

const person = computed(() => (props.sheet.kind === 'person' ? data.value?.personById.get(props.sheet.id) ?? null : null))
const personPlace = computed(() => {
  const regionId = person.value?.region_id
  if (regionId == null) return null
  return data.value?.regionById.get(regionId) ?? null
})
const personClaims = computed(() => {
  const pack = data.value
  const current = person.value
  if (!pack || !current) return []
  const ids = new Set(pack.claimsByPerson.get(current.id) ?? [])
  return pack.claims.filter((row) => ids.has(row.id)).slice(0, 12)
})

const place = computed(() => (props.sheet.kind === 'place' ? data.value?.regionById.get(props.sheet.id) ?? null : null))
const placeTrail = computed(() => {
  const row = place.value
  const pack = data.value
  if (!row || !pack) return ''
  return ancestors(row, pack.regionById).map((item) => item.name).join(' · ')
})
const placeClaims = computed(() => {
  const row = place.value
  const pack = data.value
  if (!row || !pack) return []
  return pack.claims.filter((rowClaim) => rowClaim.region_ids.includes(row.id)).slice(0, 12)
})

const polity = computed(() => (props.sheet.kind === 'polity' ? data.value?.polityById.get(props.sheet.id) ?? null : null))
const polityTitle = computed(() => (polity.value ? polityName(polity.value) : ''))
const polityLatin = computed(() => {
  const row = polity.value
  if (!row || !row.name || row.name === polityTitle.value) return ''
  return row.name
})

function labelOf(row: Claim): string {
  const title = row.event_id == null ? '' : data.value?.eventById.get(row.event_id)?.title ?? ''
  return title || row.text
}

function citationLabel(citation: Citation): string {
  return [citation.source_title, citation.edition_label, citation.locator].filter((part) => part && part !== '维基百科条目' && part !== '条目正文').join(' · ')
}

function wikipediaHref(title: string): string {
  if (title.startsWith('http')) return title
  return `https://en.wikipedia.org/wiki/${encodeURIComponent(title.replaceAll(' ', '_'))}`
}

function lookClaim() {
  const row = claim.value
  const region = claimPlace.value
  if (!row || !region) return
  emit('look', { year: row.start_year, lon: region.longitude, lat: region.latitude })
}

function lookPerson() {
  const current = person.value
  const region = personPlace.value
  if (!current || !region) return
  emit('look', { year: current.birth_year ?? 1521, lon: region.longitude, lat: region.latitude })
}

function lookPlace() {
  const row = place.value
  if (!row) return
  const span = row.polity_spans.find((item) => item.length >= 2)
  emit('look', { year: span ? clampYear(span[0]) : 1521, lon: row.longitude, lat: row.latitude })
}

function onHandle(event: PointerEvent) {
  if ((event.target as HTMLElement).closest('button')) return
  const startY = event.clientY
  const startTall = tall.value
  function move(ev: PointerEvent) {
    if (startY - ev.clientY > 28) tall.value = true
    if (ev.clientY - startY > 28) tall.value = false
  }
  function up() {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    if (tall.value === startTall && Math.abs(event.clientY - startY) < 4) tall.value = !tall.value
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}
</script>
