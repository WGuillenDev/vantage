import { useEffect, useState } from 'react'
import { loadAreas, loadZoneFile, type Area } from './storage.ts'
import { useAppStore } from './store.ts'
import type { CorridorGraph } from './mapCorridor.ts'
import type { BaselineEntry, DetailUnit } from './segmentDetail.ts'
import type { TrustMeta } from './trustSignals.ts'
import { resolveActiveZone } from './zones.ts'

export interface ZoneData {
  zone: Area
  meta: TrustMeta
  graph: CorridorGraph
  units: DetailUnit[]
  baseline: BaselineEntry[]
}

// Loads the active zone's files (map-corridor): the store's zone, then ?area, then the first validated.
// Returns null while loading and the error message if a file fails.
export function useZoneData(): ZoneData | string | null {
  const activeId = useAppStore((state) => state.activeZoneId)
  const [loaded, setLoaded] = useState<{ key: string | null; value: ZoneData | string } | null>(null)

  useEffect(() => {
    let cancelled = false
    loadAreas()
      .then(async (areas) => {
        const zone = resolveActiveZone(areas, activeId, new URLSearchParams(window.location.search).get('area'))
        if (!zone) throw new Error('areas.json lists no zones')
        const [meta, graph, scenarios] = await Promise.all([
          loadZoneFile<ZoneData['meta']>(zone.id, 'meta.json'),
          loadZoneFile<ZoneData['graph']>(zone.id, 'graph.json'),
          loadZoneFile<{ candidates: DetailUnit[]; baseline: BaselineEntry[] }>(zone.id, 'scenarios.json'),
        ])
        if (!cancelled) setLoaded({ key: activeId, value: { zone, meta, graph, units: scenarios.candidates, baseline: scenarios.baseline ?? [] } })
      })
      .catch((reason: unknown) => {
        if (!cancelled) setLoaded({ key: activeId, value: reason instanceof Error ? reason.message : String(reason) })
      })
    return () => {
      cancelled = true
    }
  }, [activeId])

  // A result of another zone is not shown while the new one loads (INV-11).
  return loaded !== null && loaded.key === activeId ? loaded.value : null
}
