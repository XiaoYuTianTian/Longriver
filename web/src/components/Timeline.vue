<template>
  <div
    ref="root"
    class="timeline"
    tabindex="0"
    aria-label="时间轴"
    @keydown="onKey"
  >
    <canvas ref="canvas" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { chinaEras, formatYear, TIMELINE_END, TIMELINE_START, worldEras, clampYear, type Era } from '../lib/format'
import { DECADE } from '../lib/density'

const props = defineProps<{
  year: number
  counts: Uint32Array
}>()

const emit = defineEmits<{ change: [year: number] }>()

const root = ref<HTMLDivElement | null>(null)
const canvas = ref<HTMLCanvasElement | null>(null)

const windowStart = ref(props.year - 50)
const windowEnd = ref(props.year + 50)
const hoverYear = ref<number | null>(null)

let width = 1
let height = 1
let dragging: 'play' | 'pan' | null = null
let moved = false
let lastX = 0
let observer: ResizeObserver | null = null

const bandColors = ['#efe4d4', '#e3ebe4', '#efe6c4', '#e2ebf0', '#f0e3da']

function tickStep(span: number): number {
  if (span > 2000) return 500
  if (span > 500) return 100
  if (span > 100) return 10
  return 1
}

function labelEvery(span: number, step: number): number {
  if (step > 1) return step
  if (span > 70) return 10
  if (span > 36) return 5
  if (span > 18) return 2
  return 1
}

function clampWindow() {
  let span = windowEnd.value - windowStart.value
  const maxSpan = TIMELINE_END - TIMELINE_START
  span = Math.min(maxSpan, Math.max(8, span))
  if (windowStart.value < TIMELINE_START) {
    windowStart.value = TIMELINE_START
    windowEnd.value = TIMELINE_START + span
  }
  if (windowEnd.value > TIMELINE_END) {
    windowEnd.value = TIMELINE_END
    windowStart.value = TIMELINE_END - span
  }
  if (windowStart.value < TIMELINE_START) windowStart.value = TIMELINE_START
}

function xOf(year: number): number {
  const span = Math.max(1, windowEnd.value - windowStart.value)
  return ((year - windowStart.value) / span) * width
}

function yearAt(x: number): number {
  const span = Math.max(1, windowEnd.value - windowStart.value)
  return clampYear(Math.round(windowStart.value + (x / Math.max(width, 1)) * span))
}

function shortYear(year: number): string {
  if (year < 0) return `前${-year}`
  if (year === 0) return '前1'
  return String(year)
}

function draw() {
  const node = canvas.value
  if (!node) return
  const ctx = node.getContext('2d')
  if (!ctx) return
  const dpr = window.devicePixelRatio || 1
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, width, height)
  ctx.fillStyle = '#f7f3ea'
  ctx.fillRect(0, 0, width, height)

  const pad = 8
  const bandH = 18
  const worldTop = pad
  const chinaTop = worldTop + bandH + 3
  const axisY = chinaTop + bandH + 22
  const densityTop = axisY + 8
  const densityH = Math.max(12, height - densityTop - 8)

  drawBands(ctx, worldEras, worldTop, bandH)
  drawBands(ctx, chinaEras, chinaTop, bandH)

  const span = Math.max(1, windowEnd.value - windowStart.value)
  const step = tickStep(span)
  const labeledStep = labelEvery(span, step)
  const play = xOf(props.year)
  ctx.strokeStyle = 'rgba(28, 25, 21, 0.75)'
  ctx.lineWidth = 1.4
  ctx.beginPath()
  ctx.moveTo(0, axisY)
  ctx.lineTo(width, axisY)
  ctx.stroke()

  ctx.font = '11px "Source Han Serif SC", "Noto Serif SC", serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'bottom'
  let lastLabelRight = -Infinity
  let tick = Math.ceil(windowStart.value / step) * step
  while (tick <= windowEnd.value) {
    const x = xOf(tick)
    const labeled = tick % labeledStep === 0
    ctx.strokeStyle = labeled ? 'rgba(28, 25, 21, 0.55)' : 'rgba(28, 25, 21, 0.22)'
    ctx.beginPath()
    ctx.moveTo(x, axisY)
    ctx.lineTo(x, axisY - (labeled ? 7 : 4))
    ctx.stroke()
    if (labeled && Math.abs(x - play) > 34) {
      const label = shortYear(tick)
      const labelWidth = ctx.measureText(label).width
      const leftEdge = x - labelWidth / 2
      if (leftEdge > lastLabelRight + 8 && x + labelWidth / 2 < width - 4) {
        ctx.fillStyle = '#5c564e'
        ctx.fillText(label, x, axisY - 8)
        lastLabelRight = x + labelWidth / 2
      }
    }
    tick += step
  }

  const first = Math.max(0, Math.floor((windowStart.value - TIMELINE_START) / DECADE))
  const last = Math.min(props.counts.length - 1, Math.floor((windowEnd.value - TIMELINE_START) / DECADE))
  let peak = 1
  for (let index = first; index <= last; index += 1) peak = Math.max(peak, props.counts[index] ?? 0)
  const binSpan = DECADE
  for (let index = first; index <= last; index += 1) {
    const count = props.counts[index] ?? 0
    if (!count) continue
    const start = TIMELINE_START + index * binSpan
    const left = xOf(start)
    const right = xOf(start + binSpan)
    const bar = Math.min(22, densityH) * (0.2 + 0.8 * (count / peak))
    ctx.fillStyle = 'rgba(31, 78, 95, 0.42)'
    ctx.beginPath()
    ctx.roundRect(left + 1, densityTop + densityH - bar, Math.max(2, right - left - 2), bar, 2)
    ctx.fill()
  }

  if (hoverYear.value != null && hoverYear.value !== props.year) {
    const x = xOf(hoverYear.value)
    ctx.strokeStyle = 'rgba(31, 78, 95, 0.35)'
    ctx.setLineDash([3, 3])
    ctx.beginPath()
    ctx.moveTo(x, worldTop)
    ctx.lineTo(x, densityTop + densityH)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = '#1f4e5f'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText(formatYear(hoverYear.value), Math.min(width - 36, Math.max(36, x)), worldTop - 1)
  }

  ctx.strokeStyle = '#8a6232'
  ctx.lineWidth = 1.5
  ctx.beginPath()
  ctx.moveTo(play, worldTop)
  ctx.lineTo(play, densityTop + densityH)
  ctx.stroke()
  ctx.fillStyle = '#f7f3ea'
  ctx.beginPath()
  ctx.arc(play, axisY, 8, 0, Math.PI * 2)
  ctx.fill()
  ctx.fillStyle = '#8a6232'
  ctx.beginPath()
  ctx.arc(play, axisY, 5.5, 0, Math.PI * 2)
  ctx.fill()
  ctx.font = '12px "Source Han Serif SC", "Noto Serif SC", serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'bottom'
  ctx.fillStyle = '#8a6232'
  ctx.fillText(formatYear(props.year), Math.min(width - 42, Math.max(42, play)), axisY - 12)
}

function drawBands(ctx: CanvasRenderingContext2D, eras: Era[], top: number, bandH: number) {
  ctx.font = '12px "Source Han Serif SC", "Noto Serif SC", serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  eras.forEach((era, index) => {
    const left = Math.max(0, xOf(era.start))
    const right = Math.min(width, xOf(era.end))
    if (right - left < 2) return
    const chosen = props.year >= era.start && props.year <= era.end
    ctx.fillStyle = chosen ? 'rgba(31, 78, 95, 0.22)' : bandColors[index % bandColors.length]
    ctx.beginPath()
    ctx.roundRect(left, top, right - left - 1, bandH, 4)
    ctx.fill()
    const label = era.name
    if (ctx.measureText(label).width + 8 < right - left) {
      ctx.fillStyle = '#1c1915'
      ctx.fillText(label, (left + right) / 2, top + bandH / 2)
    }
  })
}

function resize() {
  const node = canvas.value
  if (!node) return
  const rect = node.getBoundingClientRect()
  width = Math.max(1, rect.width)
  height = Math.max(1, rect.height)
  const dpr = window.devicePixelRatio || 1
  node.width = Math.round(width * dpr)
  node.height = Math.round(height * dpr)
  draw()
}

function focusEra(era: Era) {
  const pad = Math.max(2, Math.round((era.end - era.start) * 0.04))
  windowStart.value = era.start - pad
  windowEnd.value = era.end + pad
  clampWindow()
  emit('change', clampYear(Math.round((era.start + era.end) / 2)))
  draw()
}

function eraAt(x: number, y: number): Era | null {
  const worldTop = 8
  const bandH = 18
  const chinaTop = worldTop + bandH + 3
  const row = y < worldTop + bandH ? worldEras : y < chinaTop + bandH ? chinaEras : null
  if (!row) return null
  const year = yearAt(x)
  return row.find((era) => year >= era.start && year <= era.end) ?? null
}

function onPointerDown(event: PointerEvent) {
  const node = canvas.value
  if (!node) return
  root.value?.focus()
  const rect = node.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  const era = eraAt(x, y)
  if (era) {
    focusEra(era)
    return
  }
  moved = false
  lastX = x
  dragging = Math.abs(x - xOf(props.year)) < 14 ? 'play' : 'pan'
  node.setPointerCapture(event.pointerId)
}

function onPointerMove(event: PointerEvent) {
  const node = canvas.value
  if (!node) return
  const rect = node.getBoundingClientRect()
  const x = event.clientX - rect.left
  hoverYear.value = yearAt(x)
  if (!dragging) {
    node.style.cursor = Math.abs(x - xOf(props.year)) < 14 ? 'ew-resize' : 'grab'
    draw()
    return
  }
  if (Math.abs(x - lastX) > 2) moved = true
  if (dragging === 'play') emit('change', yearAt(x))
  if (dragging === 'pan' && moved) {
    const years = ((x - lastX) / Math.max(width, 1)) * (windowEnd.value - windowStart.value)
    windowStart.value -= years
    windowEnd.value -= years
    clampWindow()
    lastX = x
  }
  draw()
}

function onPointerUp(event: PointerEvent) {
  const node = canvas.value
  if (!node) return
  const rect = node.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  if (dragging && !moved && !eraAt(x, y)) emit('change', yearAt(x))
  dragging = null
  moved = false
  draw()
}

function onPointerLeave() {
  if (dragging) return
  hoverYear.value = null
  draw()
}

function onWheel(event: WheelEvent) {
  event.preventDefault()
  const node = canvas.value
  if (!node) return
  const rect = node.getBoundingClientRect()
  const x = event.clientX - rect.left
  const fraction = Math.min(1, Math.max(0, x / Math.max(width, 1)))
  const focus = windowStart.value + fraction * (windowEnd.value - windowStart.value)
  const factor = Math.min(2, Math.max(0.5, Math.exp(event.deltaY * 0.0016)))
  const span = Math.min(TIMELINE_END - TIMELINE_START, Math.max(8, (windowEnd.value - windowStart.value) * factor))
  windowStart.value = focus - fraction * span
  windowEnd.value = windowStart.value + span
  clampWindow()
  hoverYear.value = yearAt(x)
  draw()
}

function onKey(event: KeyboardEvent) {
  const step = event.altKey ? 100 : event.shiftKey ? 10 : 1
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault()
    event.stopPropagation()
    emit('change', clampYear(props.year + (event.key === 'ArrowRight' ? step : -step)))
  }
}

function recenter(year: number) {
  if (year >= windowStart.value && year <= windowEnd.value) return
  const span = Math.max(8, windowEnd.value - windowStart.value)
  windowStart.value = year - span / 2
  windowEnd.value = year + span / 2
  clampWindow()
}

watch(() => props.year, (year) => {
  recenter(year)
  draw()
})
watch(() => props.counts, () => draw())

onMounted(() => {
  clampWindow()
  resize()
  const node = canvas.value
  node?.addEventListener('pointerdown', onPointerDown)
  node?.addEventListener('pointermove', onPointerMove)
  node?.addEventListener('pointerup', onPointerUp)
  node?.addEventListener('pointerleave', onPointerLeave)
  root.value?.addEventListener('wheel', onWheel, { passive: false })
  observer = new ResizeObserver(() => resize())
  if (root.value) observer.observe(root.value)
  document.fonts?.ready.then(() => draw()).catch(() => undefined)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  const node = canvas.value
  node?.removeEventListener('pointerdown', onPointerDown)
  node?.removeEventListener('pointermove', onPointerMove)
  node?.removeEventListener('pointerup', onPointerUp)
  node?.removeEventListener('pointerleave', onPointerLeave)
  root.value?.removeEventListener('wheel', onWheel)
})
</script>
