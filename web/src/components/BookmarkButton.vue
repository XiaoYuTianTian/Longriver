<template>
  <button type="button" class="text-button" @click="toggle">{{ saved ? '已收藏' : '收藏' }}</button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { bookmarks, removeBookmark, saveBookmark } from '../lib/bookmarks'
import type { BookmarkKind } from '../lib/types'

const props = defineProps<{ kind: BookmarkKind; targetId: number }>()
const saved = computed(() => bookmarks.value.some((row) => row.kind === props.kind && row.targetId === props.targetId))

async function toggle() {
  const current = bookmarks.value.find((row) => row.kind === props.kind && row.targetId === props.targetId)
  if (current) await removeBookmark(props.kind, props.targetId)
  else await saveBookmark(props.kind, props.targetId, '')
}
</script>
