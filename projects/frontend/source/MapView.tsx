import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { useEffect, useRef, useState } from 'react'
import { alternateEdgeIds, alternateFeatures, alternateRoads, closedFeatures } from './closureWhatif.ts'
import { colorForCriticality, fitBounds, GRAY, legendRange, pointFeatures, rankingUnknown, unitFeatures } from './mapCorridor.ts'
import { useAppStore } from './store.ts'
import type { ZoneData } from './zoneData.ts'

// maplibre-gl 6 does not find its worker by itself when Vite bundles the page.
maplibregl.setWorkerUrl(workerUrl)

const EMPTY = { type: 'FeatureCollection' as const, features: [] }
const CLICK_TOLERANCE = 6 // px around the pointer, so thin roads are easy to hit

const SOURCES = ['units', 'hospitals', 'communities', 'closed', 'alternates']
const CLOSED_COLOR = '#b91c1c'
const ALTERNATE_COLOR = '#0284c7'

function Legend({ data, hasClosed }: { data: ZoneData; hasClosed: boolean }) {
  const { min, max } = legendRange(data.units)
  const format = new Intl.NumberFormat('es').format
  const range = { min, max }
  const gradient = [0, 0.25, 0.5, 0.75, 1]
    .map((t) => colorForCriticality(min + (max - min) * t, range))
    .join(', ')
  return (
    <div className="absolute bottom-2 left-2 rounded bg-white/90 px-2 py-1 text-xs shadow" aria-label="Leyenda de criticidad">
      <p className="font-semibold">Criticidad del tramo</p>
      <div className="mt-1 h-2 w-40 rounded" style={{ background: `linear-gradient(to right, ${gradient})` }} />
      <p className="flex w-40 justify-between">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </p>
      {rankingUnknown(data.units) && (
        <p className="mt-1 w-40">El color no ordena los tramos: se desconoce la población.</p>
      )}
      <p className="mt-1 flex items-center gap-1">
        <span aria-hidden="true" className="inline-block h-1 w-4 rounded" style={{ background: GRAY }} />
        sin impacto
      </p>
      {hasClosed && (
        <>
          <p className="mt-1 flex items-center gap-1">
            <span aria-hidden="true" className="inline-block w-4 border-t-4 border-dashed" style={{ borderColor: CLOSED_COLOR }} />
            tramo cerrado
          </p>
          <p className="flex items-center gap-1">
            <span aria-hidden="true" className="inline-block w-4 border-t-4 border-dashed" style={{ borderColor: ALTERNATE_COLOR }} />
            rutas alternas
          </p>
        </>
      )}
      <p className="mt-1 flex items-center gap-1">
        <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full border border-white bg-red-600" />
        hospital de referencia
      </p>
      <p className="flex items-center gap-1">
        <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full border border-white bg-blue-600" />
        comunidad
      </p>
    </div>
  )
}

export function MapView({ data }: { data: ZoneData | string | null }) {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const [ready, setReady] = useState(false)
  const selected = useAppStore((state) => state.selectedUnitId)
  const closed = useAppStore((state) => state.closedUnitIds)

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
        layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
      },
    })
    mapRef.current = map
    map.on('load', () => {
      for (const id of SOURCES) map.addSource(id, { type: 'geojson', data: EMPTY })
      // closure-whatif: the alternate roads sit under the units, the closed units on top of them.
      map.addLayer({
        id: 'alternates-line',
        type: 'line',
        source: 'alternates',
        paint: { 'line-color': ALTERNATE_COLOR, 'line-width': 5, 'line-dasharray': [2, 1.5] },
      })
      map.addLayer({ id: 'units-casing', type: 'line', source: 'units', paint: { 'line-color': '#ffffff', 'line-width': 7 } })
      map.addLayer({ id: 'units-line', type: 'line', source: 'units', paint: { 'line-color': ['get', 'color'], 'line-width': 4 } })
      map.addLayer({
        id: 'units-selected',
        type: 'line',
        source: 'units',
        filter: ['==', ['get', 'id'], ''],
        paint: { 'line-color': '#f59e0b', 'line-width': 9, 'line-opacity': 0.9 },
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
        type: 'circle',
        source: 'communities',
        paint: { 'circle-radius': 5, 'circle-color': '#2563eb', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 1.5 },
      })
      map.addLayer({
        id: 'hospitals',
        type: 'circle',
        source: 'hospitals',
        paint: { 'circle-radius': 7, 'circle-color': '#dc2626', 'circle-stroke-color': '#ffffff', 'circle-stroke-width': 2 },
      })
      setReady(true)
    })
    // INV-09: a click on a unit selects it; a click anywhere else clears the selection.
    map.on('click', (event) => {
      const { x, y } = event.point
      const hit = map.queryRenderedFeatures(
        [
          [x - CLICK_TOLERANCE, y - CLICK_TOLERANCE],
          [x + CLICK_TOLERANCE, y + CLICK_TOLERANCE],
        ],
        { layers: ['units-line'] },
      )[0]
      const id = hit?.properties?.id
      useAppStore.getState().selectUnit(typeof id === 'string' ? id : null)
    })
    map.on('mousemove', 'units-line', () => (map.getCanvas().style.cursor = 'pointer'))
    map.on('mouseleave', 'units-line', () => (map.getCanvas().style.cursor = ''))
    // The canvas is sized before the layout settles; follow the container so the map fills it.
    const observer = new ResizeObserver(() => map.resize())
    observer.observe(element)
    return () => {
      observer.disconnect()
      setReady(false)
      mapRef.current = null
      map.remove()
    }
  }, [])

  // INV-11 / INV-14: replace the previous zone's layers and fit the new bbox.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const set = (id: string, collection: typeof EMPTY) => (map.getSource(id) as maplibregl.GeoJSONSource).setData(collection)
    if (typeof data !== 'object' || data === null) {
      for (const id of SOURCES) set(id, EMPTY)
      return
    }
    const points = pointFeatures(data.graph)
    set('units', unitFeatures(data.graph, data.units) as unknown as typeof EMPTY)
    set('hospitals', points.hospitals as unknown as typeof EMPTY)
    set('communities', points.communities as unknown as typeof EMPTY)
    map.fitBounds(fitBounds(data.zone.bbox), { padding: 24, animate: false })
  }, [data, ready])

  useEffect(() => {
    const map = mapRef.current
    if (map && ready) map.setFilter('units-selected', ['==', ['get', 'id'], selected ?? ''])
  }, [selected, ready])

  // INV-12: the closed units and the roads named like their alternates follow the closed set.
  useEffect(() => {
    const map = mapRef.current
    if (!map || !ready) return
    const set = (id: string, collection: typeof EMPTY) => (map.getSource(id) as maplibregl.GeoJSONSource).setData(collection)
    if (typeof data !== 'object' || data === null) {
      set('closed', EMPTY)
      set('alternates', EMPTY)
      return
    }
    const names = alternateRoads(data.units, closed)
    set('closed', closedFeatures(data.graph, data.units, closed) as unknown as typeof EMPTY)
    set('alternates', alternateFeatures(data.graph.edges, alternateEdgeIds(data.graph.edges, names)) as unknown as typeof EMPTY)
  }, [data, closed, ready])

  return (
    <div className="absolute inset-0">
      <div ref={container} className="h-full w-full" />
      {typeof data === 'object' && data !== null && <Legend data={data} hasClosed={closed.length > 0} />}
    </div>
  )
}
