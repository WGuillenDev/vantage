import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef, useState } from 'react'
import { ALTERNATE_COLOR, CLOSED_COLOR, SELECTED_COLOR } from './colors.ts'
import { alternateEdgeIds, alternateFeatures, alternateRoads, closedFeatures } from './closureWhatif.ts'
import { fitBounds, pointFeatures, unitFeatures } from './mapCorridor.ts'
import { iconDataUrl, type PointKind } from './mapIcons.tsx'
import { MapLegend } from './MapLegend.tsx'
import { rowView } from './ranking.ts'
import { useAppStore } from './store.ts'
import { readyData, type ZoneData, type ZoneState } from './zoneData.ts'

// maplibre-gl 6 does not find its worker by itself when Vite bundles the page.
maplibregl.setWorkerUrl(workerUrl)

const EMPTY = { type: 'FeatureCollection' as const, features: [] }
const CLICK_TOLERANCE = 6 // px around the pointer, so thin roads are easy to hit
const NONE = ['==', ['get', 'id'], ''] as maplibregl.FilterSpecification

const SOURCES = ['units', 'hospitals', 'communities', 'closed', 'alternates']

const ICON_SIZE = 24 // css px; drawn at 2x so it stays sharp

async function addPointIcon(map: maplibregl.Map, kind: PointKind) {
  const image = new Image(ICON_SIZE * 2, ICON_SIZE * 2)
  image.src = iconDataUrl(kind, ICON_SIZE * 2)
  await image.decode()
  map.addImage(kind, image, { pixelRatio: 2 })
}

const setSource = (map: maplibregl.Map, id: string, collection: unknown) =>
  (map.getSource(id) as maplibregl.GeoJSONSource).setData(collection as typeof EMPTY)

const idFilter = (id: string | null) => (id === null ? NONE : (['==', ['get', 'id'], id] as maplibregl.FilterSpecification))

type Position = [number, number]

function unitBounds(collection: ReturnType<typeof unitFeatures>, id: string): maplibregl.LngLatBounds | null {
  const feature = collection.features.find((item) => item.properties.id === id)
  if (!feature) return null
  const bounds = new maplibregl.LngLatBounds()
  for (const line of feature.geometry.coordinates as Position[][]) for (const point of line) bounds.extend(point)
  return bounds
}

export function MapView({ state }: { state: ZoneState }) {
  const data = readyData(state)
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const dataRef = useRef<ZoneData | null>(null)
  const popup = useRef<maplibregl.Popup | null>(null)
  const [ready, setReady] = useState(false)
  const selected = useAppStore((s) => s.selectedUnitId)
  const hovered = useAppStore((s) => s.hoveredUnitId)
  const closed = useAppStore((s) => s.closedUnitIds)
  useEffect(() => {
    dataRef.current = data
  }, [data])

  useEffect(() => {
    const element = container.current
    if (!element) return
    const map = new maplibregl.Map({
      container: element,
      center: [-84, 10],
      zoom: 6,
      style: {
        version: 8,
        sources: {
          osm: {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            maxzoom: 19,
            attribution: '© colaboradores de OpenStreetMap',
          },
        },
        // Muted base map so the criticality colors carry the eye.
        layers: [{ id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-saturation': -0.75, 'raster-contrast': -0.1, 'raster-brightness-min': 0.08 } }],
      },
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
    map.on('load', async () => {
      await Promise.all([addPointIcon(map, 'community'), addPointIcon(map, 'hospital')])
      if (mapRef.current !== map) return // unmounted while the icons were loading
      for (const id of SOURCES) map.addSource(id, { type: 'geojson', data: EMPTY })
      // closure-whatif: the alternate roads sit under the units, the closed units on top of them.
      map.addLayer({
        id: 'alternates-line',
        type: 'line',
        source: 'alternates',
        paint: { 'line-color': ALTERNATE_COLOR, 'line-width': 5, 'line-dasharray': [2, 1.5] },
      })
      map.addLayer({ id: 'units-casing', type: 'line', source: 'units', paint: { 'line-color': '#ffffff', 'line-width': 7 } })
      map.addLayer({
        id: 'units-hover',
        type: 'line',
        source: 'units',
        filter: NONE,
        paint: { 'line-color': SELECTED_COLOR, 'line-width': 8, 'line-opacity': 0.45 },
      })
      map.addLayer({ id: 'units-line', type: 'line', source: 'units', paint: { 'line-color': ['get', 'color'], 'line-width': 4 } })
      map.addLayer({
        id: 'units-selected',
        type: 'line',
        source: 'units',
        filter: NONE,
        paint: { 'line-color': SELECTED_COLOR, 'line-width': 9, 'line-opacity': 0.9 },
      })
      map.moveLayer('units-line')
      map.addLayer({
        id: 'closed-line',
        type: 'line',
        source: 'closed',
        paint: { 'line-color': CLOSED_COLOR, 'line-width': 4, 'line-dasharray': [1.5, 1] },
      })
      map.addLayer({
        id: 'communities',
        type: 'symbol',
        source: 'communities',
        layout: { 'icon-image': 'community', 'icon-size': 0.8, 'icon-allow-overlap': true },
      })
      map.addLayer({
        id: 'hospitals',
        type: 'symbol',
        source: 'hospitals',
        layout: { 'icon-image': 'hospital', 'icon-allow-overlap': true },
      })
      setReady(true)
    })
    // The layers exist only after `load`; an earlier pointer event must not query them.
    const loaded = () => map.getLayer('units-line') !== undefined
    const unitAt = (point: { x: number; y: number }) =>
      !loaded()
        ? undefined
        : map.queryRenderedFeatures(
        [
          [point.x - CLICK_TOLERANCE, point.y - CLICK_TOLERANCE],
          [point.x + CLICK_TOLERANCE, point.y + CLICK_TOLERANCE],
        ],
        { layers: ['units-line'] },
      )[0]?.properties?.id as string | undefined
    // INV-09: a click on a unit selects it; a click anywhere else clears the selection.
    map.on('click', (event) => useAppStore.getState().selectUnit(unitAt(event.point) ?? null))
    // The pointer over a point shows its name; over a unit, its label and extra time, and the unit is highlighted like in the list.
    map.on('mousemove', (event) => {
      if (!loaded()) return
      const { x, y } = event.point
      const point = map.queryRenderedFeatures([[x - 4, y - 4], [x + 4, y + 4]], { layers: ['hospitals', 'communities'] })[0]
      const id = point ? undefined : unitAt(event.point)
      map.getCanvas().style.cursor = id ? 'pointer' : ''
      const current = dataRef.current
      const unit = id && current ? current.units.find((item) => item.id === id) : undefined
      const text =
        typeof point?.properties?.name === 'string'
          ? point.properties.name
          : unit && current
            ? `${rowView(unit, current.graph.edges, 0).label} · ${rowView(unit, current.graph.edges, 0).extraTime}`
            : null
      if (text === null) return void popup.current?.remove()
      popup.current ??= new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10 })
      popup.current.setLngLat(event.lngLat).setText(text).addTo(map)
    })
    map.on('mouseout', () => popup.current?.remove())
    // The canvas is sized before the layout settles; follow the container so the map fills it.
    const observer = new ResizeObserver(() => map.resize())
    observer.observe(element)
    return () => {
      observer.disconnect()
      popup.current?.remove()
      popup.current = null
      setReady(false)
      mapRef.current = null
      map.remove()
    }
  }, [])

  // INV-11 / INV-14: replace the previous zone's layers and fit the new bbox.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    if (data === null) {
      for (const id of SOURCES) setSource(map, id, EMPTY)
      return
    }
    const points = pointFeatures(data.graph)
    setSource(map, 'units', unitFeatures(data.graph, data.units))
    setSource(map, 'hospitals', points.hospitals)
    setSource(map, 'communities', points.communities)
    map.fitBounds(fitBounds(data.zone.bbox), { padding: 24, animate: false })
  }, [data, ready])

  // The selected unit is outlined, and the map flies to it when it is not already in view.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    map.setFilter('units-selected', idFilter(selected))
    if (selected === null || data === null) return
    const bounds = unitBounds(unitFeatures(data.graph, data.units), selected)
    const view = map.getBounds()
    if (bounds && !(view.contains(bounds.getSouthWest()) && view.contains(bounds.getNorthEast()))) {
      map.fitBounds(bounds, { padding: 80, maxZoom: 13, duration: 600 })
    }
  }, [selected, data, ready])

  useEffect(() => {
    const map = mapRef.current
    if (map && ready) map.setFilter('units-hover', idFilter(hovered))
  }, [hovered, ready])

  // INV-12: the closed units and the roads named like their alternates follow the closed set.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    if (data === null) {
      setSource(map, 'closed', EMPTY)
      setSource(map, 'alternates', EMPTY)
      return
    }
    const names = alternateRoads(data.units, closed)
    setSource(map, 'closed', closedFeatures(data.graph, data.units, closed))
    setSource(map, 'alternates', alternateFeatures(data.graph.edges, alternateEdgeIds(data.graph.edges, names)))
  }, [data, closed, ready])

  return (
    <div className="absolute inset-0">
      <div ref={container} className="h-full w-full" />
      {data !== null && <MapLegend data={data} hasClosed={closed.length > 0} />}
    </div>
  )
}
