<template>
  <label class="year-bar">
    <span>{{ formatYear(year) }}</span>
    <input
      type="range"
      :min="TIMELINE_START"
      :max="TIMELINE_END"
      :value="year"
      @input="onInput"
    />
  </label>
</template>

<script setup lang="ts">
import { TIMELINE_END, TIMELINE_START, formatYear } from '../lib/format'

defineProps<{ year: number }>()
const emit = defineEmits<{ change: [year: number] }>()

function onInput(event: Event) {
  emit('change', Number((event.target as HTMLInputElement).value))
}
</script>
