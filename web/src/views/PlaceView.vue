<template>
  <section v-if="!data" class="page-message">正在载入知识库</section>
  <article v-else-if="!place" class="page-message">这个地点不在知识包中。</article>
  <article v-else class="detail">
    <p class="actions"><router-link class="text-button" to="/browse">返回浏览</router-link></p>
    <img v-if="place.image && !failed" class="portrait wide" :src="mediaSrc(place.image)" :alt="place.name" @error="failed = true" />
    <p class="kicker">{{ trail }}</p>
    <h1>{{ place.name }}</h1>
    <p v-if="place.image_credit" class="muted">配图：{{ tidyCredit(place.image_credit) }}</p>
    <p v-if="place.description">{{ place.description }}</p>
    <p class="actions">
      <BookmarkButton kind="place" :target-id="place.id" />
      <router-link :to="{ path: '/', query: { year: String(mapYear), place: String(place.id) } }">在地图上看</router-link>
    </p>
    <h2>记述</h2>
    <p v-if="claims.length === 0" class="muted">这里还没有记述。</p>
    <router-link v-for="claim in visibleClaims" :key="claim.id" class="card link-card" :to="`/claims/${claim.id}`">
      <span class="kicker">{{ claim.time_label }}</span>
      <strong>{{ claim.text }}</strong>
    </router-link>
    <button v-if="claims.length > limit" type="button" class="text-button" @click="limit += 40">再显示一些</button>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import BookmarkButton from '../components/BookmarkButton.vue'
import { clampYear, mediaSrc, tidyCredit } from '../lib/format'
import { ancestors, knowledge } from '../lib/knowledge'

const props = defineProps<{ id: string }>()
const failed = ref(false)
const limit = ref(40)
const data = computed(() => knowledge.value)
const place = computed(() => data.value?.regionById.get(Number(props.id)) ?? null)
const trail = computed(() => {
  const row = place.value
  const pack = data.value
  if (!row || !pack) return ''
  return ancestors(row, pack.regionById).map((item) => item.name).join(' · ')
})
const claims = computed(() => {
  const row = place.value
  const pack = data.value
  if (!row || !pack) return []
  return pack.claims.filter((claim) => claim.region_ids.includes(row.id))
})
const visibleClaims = computed(() => claims.value.slice(0, limit.value))
const mapYear = computed(() => {
  const span = place.value?.polity_spans.find((item) => item.length >= 2)
  return span ? clampYear(span[0]) : 1521
})
</script>
