<template>
  <section class="browse">
    <header class="browse-head">
      <h1>我的</h1>
      <p class="muted">收藏和备注只存在这个浏览器里，不上传，也不同步到手机。</p>
    </header>
    <p v-if="bookmarks.length === 0" class="muted">还没有收藏。</p>
    <section v-for="group in groups" :key="group.kind" class="stack">
      <h2>{{ group.label }} · {{ group.rows.length }}</h2>
      <article v-for="row in group.rows" :key="row.id" class="card">
        <router-link v-if="row.href" :to="row.href">
          <strong>{{ row.title }}</strong>
          <span class="muted">{{ row.subtitle }}</span>
        </router-link>
        <p v-else>
          <strong>{{ row.title }}</strong>
          <span class="muted">{{ row.subtitle }}</span>
        </p>
        <label class="note">
          备注
          <textarea :value="row.note" rows="2" @change="onNote(row, $event)" />
        </label>
        <p class="actions">
          <router-link v-if="row.map" :to="row.map">在地图上看</router-link>
          <button type="button" class="text-button" @click="removeBookmark(row.kind, row.targetId)">取消收藏</button>
        </p>
      </article>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { bookmarks, removeBookmark, saveBookmark } from '../lib/bookmarks'
import { formatSpan, lifeSpan } from '../lib/format'
import { knowledge, polityName, type IndexedKnowledge } from '../lib/knowledge'
import type { Bookmark, BookmarkKind } from '../lib/types'

interface Row {
  id: string
  kind: BookmarkKind
  targetId: number
  title: string
  subtitle: string
  note: string
  href: string | null
  map: { path: string; query: Record<string, string> } | null
}

const groups = computed(() => {
  const pack = knowledge.value
  const rows = bookmarks.value.map((row) => present(row, pack))
  return [
    { kind: 'claim', label: '记述', rows: rows.filter((row) => row.kind === 'claim') },
    { kind: 'person', label: '人物', rows: rows.filter((row) => row.kind === 'person') },
    { kind: 'place', label: '地点', rows: rows.filter((row) => row.kind === 'place') },
    { kind: 'polity', label: '政权', rows: rows.filter((row) => row.kind === 'polity') },
  ].filter((group) => group.rows.length > 0)
})

function present(row: Bookmark, pack: IndexedKnowledge | null): Row {
  if (row.kind === 'claim') {
    const claim = pack?.claims.find((item) => item.id === row.targetId)
    const placeId = claim?.region_ids[0]
    return {
      id: row.id,
      kind: row.kind,
      targetId: row.targetId,
      title: claim ? pack?.eventById.get(claim.event_id ?? -1)?.title || claim.text : '已不在知识包中的记述',
      subtitle: claim?.time_label ?? '',
      note: row.note,
      href: claim ? `/claims/${claim.id}` : null,
      map: claim && placeId != null ? { path: '/', query: { year: String(claim.start_year), place: String(placeId) } } : null,
    }
  }
  if (row.kind === 'person') {
    const person = pack?.personById.get(row.targetId)
    return {
      id: row.id,
      kind: row.kind,
      targetId: row.targetId,
      title: person?.name ?? '已不在知识包中的人物',
      subtitle: person ? lifeSpan(person.birth_year, person.death_year) ?? '' : '',
      note: row.note,
      href: person ? `/people/${person.id}` : null,
      map: null,
    }
  }
  if (row.kind === 'place') {
    const place = pack?.regionById.get(row.targetId)
    return {
      id: row.id,
      kind: row.kind,
      targetId: row.targetId,
      title: place?.name ?? '已不在知识包中的地点',
      subtitle: place?.level ?? '',
      note: row.note,
      href: place ? `/places/${place.id}` : null,
      map: place ? { path: '/', query: { year: '1521', place: String(place.id) } } : null,
    }
  }
  const polity = pack?.polityById.get(row.targetId)
  return {
    id: row.id,
    kind: row.kind,
    targetId: row.targetId,
    title: polity ? polityName(polity) : '已不在知识包中的政权',
    subtitle: polity ? formatSpan(polity.from, polity.to) : '',
    note: row.note,
    href: null,
    map: polity ? { path: '/', query: { year: String(Math.max(polity.from, -3000)) } } : null,
  }
}

function onNote(row: Row, event: Event) {
  const value = (event.target as HTMLTextAreaElement).value
  void saveBookmark(row.kind, row.targetId, value)
}
</script>
