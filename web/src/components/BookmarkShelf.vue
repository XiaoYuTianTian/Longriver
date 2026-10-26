<template>
  <aside class="shelf">
    <header class="shelf-head">
      <h2>收藏</h2>
      <button type="button" class="text-button" @click="emit('close')">关闭</button>
    </header>
    <p class="muted">收藏和备注只留在这个浏览器里。</p>
    <p v-if="!pack" class="muted">正在载入知识库</p>
    <p v-else-if="bookmarks.length === 0" class="empty-note">还没有收藏。可以从地图或记述里加一条。</p>
    <section v-for="group in groups" :key="group.kind" class="stack">
      <h3>{{ group.label }} · {{ group.rows.length }}</h3>
      <article v-for="row in group.rows" :key="row.id" class="card">
        <button type="button" class="shelf-open" @click="emit('open', row.sheet, row.year)">
          <strong>{{ row.title }}</strong>
          <span class="muted">{{ row.subtitle }}</span>
        </button>
        <label class="note">
          备注
          <textarea :value="row.note" rows="2" @change="onNote(row, $event)" />
        </label>
        <button type="button" class="text-button" @click="removeBookmark(row.kind, row.targetId)">取消收藏</button>
      </article>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { bookmarks, removeBookmark, saveBookmark } from '../lib/bookmarks'
import { formatSpan, lifeSpan } from '../lib/format'
import { knowledge, polityName } from '../lib/knowledge'
import type { Bookmark, BookmarkKind } from '../lib/types'
import type { Sheet } from './DetailSheet.vue'

interface Row {
  id: string
  kind: BookmarkKind
  targetId: number
  title: string
  subtitle: string
  note: string
  year: number
  sheet: Sheet
}

const emit = defineEmits<{
  close: []
  open: [sheet: Sheet, year: number]
}>()

const pack = computed(() => knowledge.value)

const groups = computed(() => {
  const data = pack.value
  if (!data) return []
  const rows = bookmarks.value.flatMap((row) => {
    const presented = present(row)
    return presented ? [presented] : []
  })
  return [
    { kind: 'claim' as const, label: '记述', rows: rows.filter((row) => row.kind === 'claim') },
    { kind: 'person' as const, label: '人物', rows: rows.filter((row) => row.kind === 'person') },
    { kind: 'place' as const, label: '地点', rows: rows.filter((row) => row.kind === 'place') },
    { kind: 'polity' as const, label: '政权', rows: rows.filter((row) => row.kind === 'polity') },
  ].filter((group) => group.rows.length > 0)
})

function present(row: Bookmark): Row | null {
  const data = pack.value
  if (!data) return null
  if (row.kind === 'claim') {
    const claim = data.claims.find((item) => item.id === row.targetId)
    if (!claim) return { ...base(row), title: '已不在知识包中的记述', subtitle: '', year: 1521, sheet: { kind: 'claim', id: row.targetId } }
    return {
      ...base(row),
      title: data.eventById.get(claim.event_id ?? -1)?.title || claim.text,
      subtitle: claim.time_label,
      year: claim.start_year,
      sheet: { kind: 'claim', id: claim.id },
    }
  }
  if (row.kind === 'person') {
    const person = data.personById.get(row.targetId)
    if (!person) return { ...base(row), title: '已不在知识包中的人物', subtitle: '', year: 1521, sheet: { kind: 'person', id: row.targetId } }
    return {
      ...base(row),
      title: person.name,
      subtitle: lifeSpan(person.birth_year, person.death_year) ?? '',
      year: person.birth_year ?? 1521,
      sheet: { kind: 'person', id: person.id },
    }
  }
  if (row.kind === 'place') {
    const place = data.regionById.get(row.targetId)
    if (!place) return { ...base(row), title: '已不在知识包中的地点', subtitle: '', year: 1521, sheet: { kind: 'place', id: row.targetId } }
    const span = place.polity_spans.find((item) => item.length >= 2)
    return {
      ...base(row),
      title: place.name,
      subtitle: place.level,
      year: span ? span[0] : 1521,
      sheet: { kind: 'place', id: place.id },
    }
  }
  const polity = data.polityById.get(row.targetId)
  if (!polity) return { ...base(row), title: '已不在知识包中的政权', subtitle: '', year: 1521, sheet: { kind: 'polity', id: row.targetId } }
  return {
    ...base(row),
    title: polityName(polity),
    subtitle: formatSpan(polity.from, polity.to),
    year: Math.max(polity.from, -3000),
    sheet: { kind: 'polity', id: polity.id },
  }
}

function base(row: Bookmark): Pick<Row, 'id' | 'kind' | 'targetId' | 'note'> {
  return { id: row.id, kind: row.kind, targetId: row.targetId, note: row.note }
}

function onNote(row: Row, event: Event) {
  const value = (event.target as HTMLTextAreaElement).value
  void saveBookmark(row.kind, row.targetId, value)
}
</script>
