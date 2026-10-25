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
  placed.value = props.labels.flatMap((label) => {
    const point = map!.project([label.lon, label.lat])
    if (point.x < 0 || point.y < 0 || point.x > canvas.clientWidth || point.y > canvas.clientHeight) return []
    return [{ ...label, x: point.x, y: point.y }]
  })
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
  projectLabels()
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
  map?.flyTo({ center: [lon, lat], zoom, duration: 600 })
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
    map.on('mouseenter', 'borders-fill', () => {
      if (map) map.getCanvas().style.cursor = 'pointer'
    })
    map.on('mouseleave', 'borders-fill', () => {
      if (map) map.getCanvas().style.cursor = ''
    })
    map.on('move', projectLabels)
    ready = true
    applyYear(props.year)
    applyPlaces()
  })
})

watch(() => props.year, (year) => applyYear(year))
watch(() => props.places, () => applyPlaces())
watch(() => props.labels, () => projectLabels())

onBeforeUnmount(() => {
  map?.remove()
  map = null
})
</script>
