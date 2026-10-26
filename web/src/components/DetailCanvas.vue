<template>
  <canvas ref="canvas" class="detail-canvas" role="img" :aria-label="label"></canvas>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{
  title: string
  year: string
  place: string
  sentence: string
  band: string
  image?: string | null
  note?: string
}>()

const canvas = ref<HTMLCanvasElement | null>(null)
const label = computed(() => [props.year, props.place, props.title].filter(Boolean).join('，'))
let picture: HTMLImageElement | null = null
let pictureSrc = ''
let observer: ResizeObserver | null = null

function wrap(context: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = []
  let line = ''
  for (const char of text) {
    const next = line + char
    if (context.measureText(next).width > maxWidth && line) {
      lines.push(line)
      line = char
    } else {
      line = next
    }
  }
  if (line) lines.push(line)
  return lines
}

function draw() {
  const node = canvas.value
  if (!node) return
  const width = Math.max(280, node.clientWidth)
  const height = 300
  const ratio = window.devicePixelRatio || 1
  node.width = Math.round(width * ratio)
  node.height = Math.round(height * ratio)
  node.style.height = `${height}px`
  const context = node.getContext('2d')
  if (!context) return
  context.setTransform(ratio, 0, 0, ratio, 0, 0)
  context.fillStyle = '#f7f3ea'
  context.fillRect(0, 0, width, height)
  context.fillStyle = props.band || '#1f4e5f'
  context.fillRect(0, 0, 8, height)

  const imageWidth = picture ? Math.min(220, width * 0.38) : 0
  const textWidth = width - 48 - (imageWidth ? imageWidth + 24 : 0)
  context.fillStyle = '#1a2421'
  context.font = '56px Fraunces, "Palatino Linotype", "Noto Serif SC", serif'
  context.fillText(props.year || '—', 28, 72)
  context.font = '16px "Noto Serif SC", serif'
  context.fillStyle = '#6d655c'
  context.fillText(props.place || '地点未标出', 28, 102)
  context.strokeStyle = '#8a6232'
  context.lineWidth = 1
  context.beginPath()
  context.moveTo(28, 118)
  context.lineTo(28 + Math.min(120, textWidth), 118)
  context.stroke()

  context.fillStyle = '#1a2421'
  context.font = '28px "Noto Serif SC", serif'
  const titleLines = wrap(context, props.title || '未题', textWidth).slice(0, 3)
  titleLines.forEach((line, index) => context.fillText(line, 28, 158 + index * 36))
  context.fillStyle = '#1a2421'
  context.font = '16px "Noto Serif SC", serif'
  const sentenceTop = 158 + titleLines.length * 36 + 8
  wrap(context, props.sentence || '', textWidth).slice(0, 4).forEach((line, index) => {
    context.fillText(line, 28, sentenceTop + index * 26)
  })

  if (picture && imageWidth) {
    const x = width - imageWidth - 20
    const y = 28
    const frame = 248
    const heightUsed = Math.min(frame, height - 56)
    context.save()
    context.beginPath()
    context.rect(x, y, imageWidth, heightUsed)
    context.clip()
    const scale = Math.max(imageWidth / picture.width, heightUsed / picture.height)
    const dw = picture.width * scale
    const dh = picture.height * scale
    context.drawImage(picture, x + (imageWidth - dw) / 2, y + (heightUsed - dh) / 2, dw, dh)
    context.restore()
    context.strokeStyle = '#8a6232'
    context.strokeRect(x, y, imageWidth, heightUsed)
  }

  if (props.note) {
    context.fillStyle = '#6d655c'
    context.font = '13px "Noto Serif SC", serif'
    context.fillText(props.note, 28, height - 18)
  }
}

function loadPicture(src: string | null | undefined) {
  if (!src) {
    picture = null
    pictureSrc = ''
    draw()
    return
  }
  if (src === pictureSrc && picture) {
    draw()
    return
  }
  const image = new Image()
  image.onload = () => {
    if (props.image !== src) return
    picture = image
    pictureSrc = src
    draw()
  }
  image.onerror = () => {
    if (props.image !== src) return
    picture = null
    pictureSrc = ''
    draw()
  }
  image.src = src
}

onMounted(() => {
  const fonts = document.fonts
  if (fonts) void fonts.ready.then(draw)
  else draw()
  if (canvas.value) {
    observer = new ResizeObserver(() => draw())
    observer.observe(canvas.value)
  }
  loadPicture(props.image)
})

watch(() => [props.title, props.year, props.place, props.sentence, props.band, props.note], () => draw())
watch(() => props.image, (src) => loadPicture(src))

onBeforeUnmount(() => observer?.disconnect())
</script>
