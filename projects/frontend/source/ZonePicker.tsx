import { useEffect, useState } from 'react'
import { loadAreas, type Area } from './storage.ts'
import { useAppStore } from './store.ts'
import { chooseZone, showsZoneControl, zoneOptions } from './zones.ts'

// Display-only fallback; `map-corridor` owns the real active-zone rule (URL, then first validated, then first).
function initialZoneId(areas: Area[]): string | undefined {
  const fromUrl = new URLSearchParams(window.location.search).get('area')
  return (areas.find((area) => area.id === fromUrl) ?? areas.find((area) => area.validated) ?? areas[0])?.id
}

export function ZonePicker() {
  const [areas, setAreas] = useState<Area[]>([])
  const activeId = useAppStore((state) => state.activeZoneId)

  useEffect(() => {
    loadAreas()
      .then(setAreas)
      .catch(() => setAreas([]))
  }, [])

  if (areas.length === 0) return null
  const current = activeId ?? initialZoneId(areas)
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
