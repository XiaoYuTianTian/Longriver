<template>
  <div class="map-stage">
    <div ref="root" class="map-canvas"></div>
    <button
      v-for="label in placed"
      :key="label.key"
      type="button"
      class="map-label"
      :class="[label.kind, { on: isActive(label) }]"
      :style="{ left: `${label.x}px`, top: `${label.y}px` }"
      @click="onLabel(label)"
    >
      {{ label.name }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { FeatureCollection, Point } from 'geojson'
import maplibregl, { type ExpressionSpecification, type FilterSpecification, type GeoJSONSource } from 'maplibre-gl'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { bucketFor } from '../lib/format'
import type { MapLabel, PlacePoint } from '../lib/types'

const props = defineProps<{
  year: number
  places: PlacePoint[]
  labels: MapLabel[]
  activePolity: number | null
  activeCountry: string
  activePlace: PlacePoint | null
  focusToken: number
}>()

const emit = defineEmits<{
  polity: [id: number]
  country: [name: string]
  place: [id: number]
}>()

const root = ref<HTMLDivElement | null>(null)
const placed = ref<Array<MapLabel & { x: number; y: number }>>([])

const palette = ['#C45A32', '#3E8A58', '#C49A1C', '#2F6F9A', '#A24E7A', '#6B7C28', '#B86A3A', '#4A5F9A']

let map: maplibregl.Map | null = null
let loadedBucket = -1
let ready = false

function paletteFill(): ExpressionSpecification {
  return [
    'match',
    ['get', 'c'],
    0, palette[0],
    1, palette[1],
    2, palette[2],
    3, palette[3],
    4, palette[4],
    5, palette[5],
    6, palette[6],
    7, palette[7],
    palette[0],
  ]
}

function yearFilter(year: number): FilterSpecification {
  return ['all', ['<=', ['get', 'f'], year], ['>=', ['get', 't'], year]]
}

function placeCollection(places: PlacePoint[]): FeatureCollection<Point> {
  return {
    type: 'FeatureCollection',
    features: places.map((place) => ({
      type: 'Feature',
      properties: { id: place.id, name: place.name },
      geometry: { type: 'Point', coordinates: [place.lon, place.lat] },
    })),
  }
}

function projectLabels() {
  if (!map) return
  const canvas = map.getCanvas()
  const width = canvas.clientWidth
  const height = canvas.clientHeight
  if (width < 10 || height < 10) return
  const boxes: Array<{ l: number; t: number; r: number; b: number }> = []
  const next: Array<MapLabel & { x: number; y: number }> = []
  const ordered = [...props.labels.filter((label) => !isActive(label)), ...props.labels.filter((label) => isActive(label))]
  for (const label of ordered) {
    const point = map.project([label.lon, label.lat])
    const boxWidth = Math.min(168, label.name.length * 14 + 22)
    const boxHeight = 28
    const inside = point.x >= 8 && point.y >= 8 && point.x <= width - 8 && point.y <= height - 8
    if (!inside && !isActive(label)) continue
    const box = {
      l: point.x - boxWidth / 2,
      t: point.y - boxHeight / 2,
      r: point.x + boxWidth / 2,
      b: point.y + boxHeight / 2,
    }
    const hits = (other: { l: number; t: number; r: number; b: number }) =>
      box.l < other.r + 8 && box.r > other.l - 8 && box.t < other.b + 8 && box.b > other.t - 8
    if (isActive(label)) {
      for (let index = boxes.length - 1; index >= 0; index -= 1) {
        if (!hits(boxes[index])) continue
        boxes.splice(index, 1)
        next.splice(index, 1)
      }
    } else if (boxes.some(hits)) {
      continue
    }
    boxes.push(box)
    next.push({ ...label, x: point.x, y: point.y })
  }
  placed.value = next
}

function applyYear(year: number) {
  if (!map || !ready) return
  const modern = year > 1911
  map.setLayoutProperty('borders-fill', 'visibility', modern ? 'none' : 'visible')
  map.setLayoutProperty('borders-line', 'visibility', modern ? 'none' : 'visible')
  map.setLayoutProperty('countries-fill', 'visibility', modern ? 'visible' : 'none')
  map.setLayoutProperty('countries-line', 'visibility', modern ? 'visible' : 'none')
  if (!modern) {
    const bucket = bucketFor(year)
    if (bucket !== loadedBucket) {
      ;(map.getSource('borders') as GeoJSONSource).setData(`/borders/${bucket}.geojson`)
      loadedBucket = bucket
    }
    const filter = yearFilter(year)
    map.setFilter('borders-fill', filter)
    map.setFilter('borders-line', filter)
  }
  applySelection()
  projectLabels()
}

function applySelection() {
  if (!map || !ready) return
  const modern = props.year > 1911
  const polityId = props.activePolity
  const activeBorders: FilterSpecification = polityId == null || modern
    ? ['==', ['get', 'p'], -1]
    : ['all', ['<=', ['get', 'f'], props.year], ['>=', ['get', 't'], props.year], ['==', ['get', 'p'], polityId]]
  map.setFilter('borders-active-fill', activeBorders)
  map.setFilter('borders-active', activeBorders)
  const activeCountry: FilterSpecification = !modern || !props.activeCountry
    ? ['==', ['get', 'n'], '']
    : ['==', ['get', 'n'], props.activeCountry]
  map.setFilter('countries-active-fill', activeCountry)
  map.setFilter('countries-active', activeCountry)
}

function applyFocus() {
  if (!map || !ready) return
  const place = props.activePlace
  const data: FeatureCollection<Point> = {
    type: 'FeatureCollection',
    features: place
      ? [{
        type: 'Feature',
        properties: { id: place.id },
        geometry: { type: 'Point', coordinates: [place.lon, place.lat] },
      }]
      : [],
  }
  ;(map.getSource('focus-place') as GeoJSONSource).setData(data)
}

function applyPlaces() {
  if (!map || !ready) return
  ;(map.getSource('places') as GeoJSONSource).setData(placeCollection(props.places))
}

function onLabel(label: MapLabel) {
  if (label.kind === 'polity' && label.id != null) emit('polity', label.id)
  if (label.kind === 'country') emit('country', label.name)
}

function isActive(label: MapLabel): boolean {
  if (label.kind === 'polity') return label.id === props.activePolity
  return label.name === props.activeCountry
}

function flyTo(lon: number, lat: number, zoom: number) {
  map?.flyTo({
    center: [lon, lat],
    zoom,
    duration: 700,
    padding: { top: 80, right: 340, bottom: 28, left: 28 },
  })
}

defineExpose({ flyTo })

onMounted(() => {
  if (!root.value) return
  map = new maplibregl.Map({
    container: root.value,
    style: {
      version: 8,
      sources: {},
      layers: [{ id: 'ocean', type: 'background', paint: { 'background-color': '#D5E3E3' } }],
    },
    center: [60, 32],
    zoom: 1.4,
    attributionControl: false,
    dragRotate: false,
    pitchWithRotate: false,
  })
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
  map.on('load', () => {
    if (!map) return
    const year = props.year
    const modern = year > 1911
    loadedBucket = bucketFor(year)
    map.addSource('land', { type: 'geojson', data: '/land.geojson' })
    map.addLayer({
      id: 'land',
      type: 'fill',
      source: 'land',
      paint: { 'fill-color': '#E7E0D4', 'fill-opacity': 1 },
    })
    map.addSource('borders', { type: 'geojson', data: `/borders/${loadedBucket}.geojson` })
    map.addLayer({
      id: 'borders-fill',
      type: 'fill',
      source: 'borders',
      filter: yearFilter(Math.min(year, 1911)),
      layout: { visibility: modern ? 'none' : 'visible' },
      paint: { 'fill-color': paletteFill(), 'fill-opacity': 0.74 },
    })
    map.addLayer({
      id: 'borders-line',
      type: 'line',
      source: 'borders',
      filter: yearFilter(Math.min(year, 1911)),
      layout: { visibility: modern ? 'none' : 'visible' },
      paint: { 'line-color': '#3F3428', 'line-width': 1.1, 'line-opacity': 0.95 },
    })
    map.addLayer({
      id: 'borders-active-fill',
      type: 'fill',
      source: 'borders',
      filter: ['==', ['get', 'p'], -1],
      paint: { 'fill-color': '#8A6232', 'fill-opacity': 0.28 },
    })
    map.addLayer({
      id: 'borders-active',
      type: 'line',
      source: 'borders',
      filter: ['==', ['get', 'p'], -1],
      paint: { 'line-color': '#8A6232', 'line-width': 2.4 },
    })
    map.addSource('countries', { type: 'geojson', data: '/countries.geojson' })
    map.addLayer({
      id: 'countries-fill',
      type: 'fill',
      source: 'countries',
      layout: { visibility: modern ? 'visible' : 'none' },
      paint: { 'fill-color': paletteFill(), 'fill-opacity': 0.74 },
    })
    map.addLayer({
      id: 'countries-line',
      type: 'line',
      source: 'countries',
      layout: { visibility: modern ? 'visible' : 'none' },
      paint: { 'line-color': '#3F3428', 'line-width': 1.1 },
    })
    map.addLayer({
      id: 'countries-active-fill',
      type: 'fill',
      source: 'countries',
      filter: ['==', ['get', 'n'], ''],
      paint: { 'fill-color': '#8A6232', 'fill-opacity': 0.28 },
    })
    map.addLayer({
      id: 'countries-active',
      type: 'line',
      source: 'countries',
      filter: ['==', ['get', 'n'], ''],
      paint: { 'line-color': '#8A6232', 'line-width': 2.4 },
    })
    map.addSource('places', { type: 'geojson', data: placeCollection(props.places) })
    map.addLayer({
      id: 'places',
      type: 'circle',
      source: 'places',
      paint: {
        'circle-radius': 5,
        'circle-color': '#8C4A32',
        'circle-stroke-width': 1,
        'circle-stroke-color': '#FFFBF5',
      },
    })
    map.addSource('focus-place', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } })
    map.addLayer({
      id: 'focus-place',
      type: 'circle',
      source: 'focus-place',
      paint: {
        'circle-radius': 8,
        'circle-color': '#8A6232',
        'circle-stroke-width': 3,
        'circle-stroke-color': '#FFFBF5',
      },
    })
    map.on('click', 'borders-fill', (event) => {
      const id = event.features?.[0]?.properties?.p
      if (id != null) emit('polity', Number(id))
    })
    map.on('click', 'countries-fill', (event) => {
      const name = event.features?.[0]?.properties?.n
      if (name) emit('country', String(name))
    })
    map.on('click', 'places', (event) => {
      const id = event.features?.[0]?.properties?.id
      if (id != null) emit('place', Number(id))
    })
    for (const layer of ['borders-fill', 'countries-fill', 'places']) {
      map.on('mouseenter', layer, () => {
        if (map) map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', layer, () => {
        if (map) map.getCanvas().style.cursor = ''
      })
    }
    map.on('move', projectLabels)
    ready = true
    applyYear(props.year)
    applyPlaces()
    applySelection()
    applyFocus()
    if (props.focusToken > 0 && props.activePlace) flyTo(props.activePlace.lon, props.activePlace.lat, 3.4)
  })
})

watch(() => props.year, (year) => applyYear(year))
watch(() => props.places, () => applyPlaces())
watch(() => props.labels, () => projectLabels())
watch(() => [props.activePolity, props.activeCountry], () => {
  applySelection()
  projectLabels()
})
watch(() => props.activePlace, (place) => {
  applyFocus()
  if (place && props.focusToken > 0) flyTo(place.lon, place.lat, 3.4)
})
watch(() => props.focusToken, () => {
  const place = props.activePlace
  if (place) flyTo(place.lon, place.lat, 3.4)
})

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>
