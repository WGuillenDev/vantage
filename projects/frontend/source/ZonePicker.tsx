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
  if (!showsZoneControl(areas)) return <span>{areas[0]?.name}</span>

  return (
    <label className="flex items-center gap-1 text-sm">
      Zona
      <select value={current} onChange={(event) => chooseZone(event.target.value)}>
        {zoneOptions(areas).map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
