import { MapPin } from 'lucide-react'
import { useEffect, useState } from 'react'
import { loadAreas, type Area } from './storage.ts'
import { useAppStore } from './store.ts'
import { chooseZone, resolveActiveZone, showsZoneControl, zoneOptions } from './zones.ts'

export function ZonePicker() {
  const [areas, setAreas] = useState<Area[]>([])
  const activeId = useAppStore((state) => state.activeZoneId)

  useEffect(() => {
    loadAreas()
      .then(setAreas)
      .catch(() => setAreas([]))
  }, [])

  if (areas.length === 0) return null
  const current = resolveActiveZone(areas, activeId, new URLSearchParams(window.location.search).get('area'))?.id
  if (!showsZoneControl(areas))
    return (
      <span className="flex items-center gap-1.5 text-sm font-medium">
        <MapPin aria-hidden="true" className="h-4 w-4 text-brand" />
        {areas[0]?.name}
      </span>
    )

  return (
    <label className="flex items-center gap-1.5 text-sm">
      <MapPin aria-hidden="true" className="h-4 w-4 text-brand" />
      <span className="sr-only sm:not-sr-only">Zona</span>
      <select className="rounded-lg border border-line bg-white px-2 py-1 max-md:min-h-11" value={current} onChange={(event) => chooseZone(event.target.value)}>
        {zoneOptions(areas).map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
