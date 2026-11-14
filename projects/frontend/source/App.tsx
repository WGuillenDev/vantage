import maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'

const STORAGE = `${import.meta.env.BASE_URL}storage/`

type Bounds = [number, number, number, number] // west, south, east, north

interface Meta {
  area: { name: string; bbox: Bounds }
  overlays: { id: string; file: string; bounds: Bounds }[]
}

async function loadMeta(): Promise<Meta> {
  const response = await fetch(`${STORAGE}meta.json`)
  if (!response.ok) {
    throw new Error(`Could not load meta.json (${response.status}); run "make mock"`)
  }
  return (await response.json()) as Meta
}

function App() {
  const container = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [areaName, setAreaName] = useState<string | null>(null)

  useEffect(() => {
    let map: maplibregl.Map | undefined
    let cancelled = false

    loadMeta()
      .then((meta) => {
        const element = container.current
        if (cancelled || !element) return
        const overlay = meta.overlays.find((item) => item.id === 'change')
        if (!overlay) throw new Error('meta.json has no "change" overlay')
        setAreaName(meta.area.name)
        const [west, south, east, north] = overlay.bounds

        map = new maplibregl.Map({
          container: element,
          bounds: meta.area.bbox,
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
        map.on('load', () => {
          map?.addSource('change', {
            type: 'image',
            url: `${STORAGE}${overlay.file}`,
            coordinates: [
              [west, north],
              [east, north],
              [east, south],
              [west, south],
            ],
          })
          map?.addLayer({
            id: 'change',
            type: 'raster',
            source: 'change',
            paint: { 'raster-opacity': 0.7 },
          })
        })
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : String(reason))
      })

    return () => {
      cancelled = true
      map?.remove()
    }
  }, [])

  return (
    <div className="relative h-full">
      <div ref={container} className="h-full" />
      <p className="absolute left-2 top-2 rounded bg-white/90 px-2 py-1 text-sm">
        {error ?? `Señal de cambio candidata · ${areaName ?? 'cargando…'}`}
      </p>
    </div>
  )
}

export default App
