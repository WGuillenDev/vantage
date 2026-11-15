import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useEffect, useRef, useState } from 'react'
import { colorForCriticality, fitBounds, GRAY, legendRange, pointFeatures, unitFeatures } from './mapCorridor.ts'
import { useAppStore } from './store.ts'
import type { ZoneData } from './zoneData.ts'

const EMPTY = { type: 'FeatureCollection' as const, features: [] }
const CLICK_TOLERANCE = 6 // px around the pointer, so thin roads are easy to hit

function Legend({ data }: { data: ZoneData }) {
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
      <p className="mt-1 flex items-center gap-1">
        <span aria-hidden="true" className="inline-block h-1 w-4 rounded" style={{ background: GRAY }} />
        sin impacto
      </p>
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
      for (const id of ['units', 'hospitals', 'communities']) map.addSource(id, { type: 'geojson', data: EMPTY })
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
    return () => {
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
      for (const id of ['units', 'hospitals', 'communities']) set(id, EMPTY)
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

  return (
    <div className="absolute inset-0">
      <div ref={container} className="h-full w-full" />
      {typeof data === 'object' && data !== null && <Legend data={data} />}
    </div>
  )
}
