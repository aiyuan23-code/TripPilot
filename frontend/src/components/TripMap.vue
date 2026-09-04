<script setup lang="ts">
import AMapLoader from '@amap/amap-jsapi-loader'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { Attraction, Location } from '@/types'

const props = defineProps<{
  attractions: Attraction[]
}>()

type MappedAttraction = Attraction & { location: Location }
type MarkerInstance = object

interface MapInstance {
  add(overlays: MarkerInstance[]): void
  setFitView(overlays?: MarkerInstance[]): void
  destroy(): void
}

interface AMapNamespace {
  Map: new (
    container: HTMLElement,
    options: { zoom: number; center: [number, number]; viewMode: string },
  ) => MapInstance
  Marker: new (options: {
    position: [number, number]
    title: string
    label: { content: string; direction: string }
  }) => MarkerInstance
}

const container = ref<HTMLElement | null>(null)
const loading = ref(false)
const errorMessage = ref('')
let map: MapInstance | null = null

const mappedAttractions = computed<MappedAttraction[]>(() =>
  props.attractions.filter(
    (item): item is MappedAttraction => item.location !== null,
  ),
)

async function renderMap(): Promise<void> {
  const key = import.meta.env.VITE_AMAP_JS_KEY?.trim()
  if (!key) {
    errorMessage.value = '请在 frontend/.env 中配置 VITE_AMAP_JS_KEY 后显示地图。'
    return
  }
  if (!container.value || mappedAttractions.value.length === 0) {
    errorMessage.value = '当前行程中没有可标记的景点坐标。'
    return
  }

  loading.value = true
  errorMessage.value = ''
  map?.destroy()
  map = null

  const securityCode = import.meta.env.VITE_AMAP_SECURITY_CODE?.trim()
  if (securityCode) {
    window._AMapSecurityConfig = { securityJsCode: securityCode }
  }

  try {
    const sdk = (await AMapLoader.load({
      key,
      version: '2.0',
    })) as unknown as AMapNamespace
    const first = mappedAttractions.value[0]
    map = new sdk.Map(container.value, {
      zoom: 12,
      center: [first.location.longitude, first.location.latitude],
      viewMode: '2D',
    })
    const markers = mappedAttractions.value.map(
      (attraction, index) =>
        new sdk.Marker({
          position: [
            attraction.location.longitude,
            attraction.location.latitude,
          ],
          title: attraction.name,
          label: {
            content: `<span class="map-marker-label">${index + 1}</span>`,
            direction: 'top',
          },
        }),
    )
    map.add(markers)
    map.setFitView(markers)
  } catch {
    errorMessage.value = '高德地图加载失败，请检查 JS API Key、安全密钥和域名配置。'
  } finally {
    loading.value = false
  }
}

onMounted(renderMap)
watch(() => props.attractions, renderMap, { deep: true })
onBeforeUnmount(() => map?.destroy())
</script>

<template>
  <div class="map-frame">
    <div ref="container" class="map-container"></div>
    <div v-if="loading" class="map-message">正在加载地图…</div>
    <div v-else-if="errorMessage" class="map-message map-message-error">
      {{ errorMessage }}
    </div>
  </div>
</template>

