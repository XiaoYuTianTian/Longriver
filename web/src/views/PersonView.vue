<template>
  <section v-if="!data" class="page-message">正在载入知识库</section>
  <article v-else-if="!person" class="page-message">这位人物不在知识包中。</article>
  <article v-else class="detail">
    <p class="actions"><router-link class="text-button" to="/browse">返回浏览</router-link></p>
    <img v-if="person.image && !failed" class="portrait" :src="mediaSrc(person.image)" :alt="person.name" @error="failed = true" />
    <h1>{{ person.name }}</h1>
    <p class="muted">{{ lifeSpan(person.birth_year, person.death_year) || '生卒未收录' }}</p>
    <p v-if="person.image_credit" class="muted">头像：{{ tidyCredit(person.image_credit) }}</p>
    <p v-if="person.description">{{ person.description }}</p>
    <p class="actions">
      <BookmarkButton kind="person" :target-id="person.id" />
      <router-link v-if="place" :to="{ path: '/', query: { year: String(person.birth_year ?? 1521), place: String(place.id) } }">在地图上看</router-link>
    </p>
    <h2>相关记述</h2>
    <p v-if="claims.length === 0" class="muted">没有关联记述。</p>
    <router-link v-for="claim in claims" :key="claim.id" class="card link-card" :to="`/claims/${claim.id}`">
      <span class="kicker">{{ claim.time_label }}</span>
      <strong>{{ claim.text }}</strong>
    </router-link>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import BookmarkButton from '../components/BookmarkButton.vue'
import { lifeSpan, mediaSrc, tidyCredit } from '../lib/format'
import { knowledge } from '../lib/knowledge'

const props = defineProps<{ id: string }>()
const failed = ref(false)
const data = computed(() => knowledge.value)
const person = computed(() => data.value?.personById.get(Number(props.id)) ?? null)
const place = computed(() => {
  const regionId = person.value?.region_id
  if (regionId == null) return null
  return data.value?.regionById.get(regionId) ?? null
})
const claims = computed(() => {
  const pack = data.value
  const current = person.value
  if (!pack || !current) return []
  const ids = new Set(pack.claimsByPerson.get(current.id) ?? [])
  return pack.claims.filter((claim) => ids.has(claim.id))
})
</script>
