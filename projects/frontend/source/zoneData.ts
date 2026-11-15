import { useEffect, useState } from 'react'
import { loadAreas, loadZoneFile, type Area } from './storage.ts'
import { useAppStore } from './store.ts'
import type { RankedUnit } from './ranking.ts'
import type { TrustMeta } from './trustSignals.ts'
import { resolveActiveZone } from './zones.ts'

export interface ZoneData {
  zone: Area
  meta: TrustMeta
  graph: { edges: { id: string; road?: string | null }[]; hospitals: { name: string }[] }
  units: RankedUnit[]
}

// Loads the active zone's files; `map-corridor` will take over zone loading and this will read from its store.
// Returns null while loading and the error message if a file fails.
export function useZoneData(): ZoneData | string | null {
  const activeId = useAppStore((state) => state.activeZoneId)
  const [data, setData] = useState<ZoneData | string | null>(null)

  useEffect(() => {
    let cancelled = false
    loadAreas()
      .then(async (areas) => {
        const zone = resolveActiveZone(areas, activeId, new URLSearchParams(window.location.search).get('area'))
        if (!zone) throw new Error('areas.json lists no zones')
        const [meta, graph, scenarios] = await Promise.all([
          loadZoneFile<ZoneData['meta']>(zone.id, 'meta.json'),
          loadZoneFile<ZoneData['graph']>(zone.id, 'graph.json'),
          loadZoneFile<{ candidates: RankedUnit[] }>(zone.id, 'scenarios.json'),
        ])
        if (!cancelled) setData({ zone, meta, graph, units: scenarios.candidates })
      })
      .catch((reason: unknown) => {
        if (!cancelled) setData(reason instanceof Error ? reason.message : String(reason))
      })
    return () => {
      cancelled = true
    }
  }, [activeId])

  return data
}
