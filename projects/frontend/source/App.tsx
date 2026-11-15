import maplibregl from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import { loadDefaultZone } from './storage.ts'

type Bounds = [number, number, number, number] // west, south, east, north

interface Meta {
  area: { name: string; bbox: Bounds }
  overlays?: { id: string; file: string; bounds: Bounds }[]
}

async function loadMeta(): Promise<{ meta: Meta; base: string }> {
  const { base } = await loadDefaultZone()
  const response = await fetch(`${base}meta.json`)
  if (!response.ok) {
    throw new Error(`Could not load meta.json (${response.status}); run "make mock"`)
  }
  return { meta: (await response.json()) as Meta, base }
}

function App() {
  const container = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [areaName, setAreaName] = useState<string | null>(null)

  useEffect(() => {
    let map: maplibregl.Map | undefined
    let cancelled = false

    loadMeta()
      .then(({ meta, base }) => {
        const element = container.current
        if (cancelled || !element) return
        const overlay = meta.overlays?.find((item) => item.id === 'change')
        setAreaName(meta.area.name)

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
          if (!overlay) return // the radar change layer is optional since 0.2
          const [west, south, east, north] = overlay.bounds
          map?.addSource('change', {
            type: 'image',
            url: `${base}${overlay.file}`,
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
