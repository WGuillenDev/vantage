import { useEffect, useRef, useState } from 'react'
import { loadAreas, loadZoneFile } from './storage.ts'
import { useAppStore } from './store.ts'
import { countWithoutImpact, listedUnits, maxCriticality, noPopulationNote, rowView, type RankedUnit } from './ranking.ts'
import { resolveActiveZone } from './zones.ts'

type Edge = { id: string; road?: string | null }

// Loads the active zone's units; `map-corridor` will take over zone loading and this will read from its store.
function useZoneUnits(): { units: RankedUnit[]; edges: Edge[] } | string | null {
  const activeId = useAppStore((state) => state.activeZoneId)
  const [data, setData] = useState<{ units: RankedUnit[]; edges: Edge[] } | string | null>(null)

  useEffect(() => {
    let cancelled = false
    loadAreas()
      .then(async (areas) => {
        const zone = resolveActiveZone(areas, activeId, new URLSearchParams(window.location.search).get('area'))
        if (!zone) throw new Error('areas.json lists no zones')
        const [scenarios, graph] = await Promise.all([
          loadZoneFile<{ candidates: RankedUnit[] }>(zone.id, 'scenarios.json'),
          loadZoneFile<{ edges: Edge[] }>(zone.id, 'graph.json'),
        ])
        if (!cancelled) setData({ units: scenarios.candidates, edges: graph.edges })
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

export function SegmentRanking() {
  const data = useZoneUnits()
  const selected = useAppStore((state) => state.selectedUnitId)
  const selectUnit = useAppStore((state) => state.selectUnit)
  const selectedRow = useRef<HTMLLIElement>(null)

  useEffect(() => {
    selectedRow.current?.scrollIntoView({ block: 'nearest' })
  }, [selected, data])

  if (data === null) return <p className="p-2 text-sm">Cargando tramos…</p>
  if (typeof data === 'string') return <p className="p-2 text-sm">{data}</p>

  const rows = listedUnits(data.units)
  const maxCrit = maxCriticality(data.units)
  const without = countWithoutImpact(data.units)

  return (
    <section className="flex h-full flex-col text-sm" aria-label="Tramos críticos">
      <h2 className="p-2 font-semibold">Tramos críticos por criticidad</h2>
      {noPopulationNote(data.units) && (
        <p className="px-2 pb-2">
          El orden sale del tiempo extra y de las comunidades aisladas, porque la población es desconocida.
        </p>
      )}
      {rows.length === 0 ? (
        <p className="p-2">Ningún tramo deja a comunidades con tiempo extra o sin ruta.</p>
      ) : (
        <ol className="min-h-0 flex-1 overflow-y-auto">
          {rows.map((unit) => {
            const row = rowView(unit, data.edges, maxCrit)
            const isSelected = unit.id === selected
            return (
              <li key={unit.id} ref={isSelected ? selectedRow : undefined}>
                <button
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => selectUnit(unit.id)}
                  className={`block w-full px-2 py-1 text-left ${isSelected ? 'bg-amber-100' : 'hover:bg-gray-100'}`}
                >
                  <span className="font-medium">{row.label}</span> · {row.length}
                  <br />
                  {row.extraTime} · {row.population}
                  {row.barFraction !== null && (
                    <span className="mt-1 block h-1.5 bg-gray-200" aria-hidden="true">
                      <span className="block h-full bg-amber-600" style={{ width: `${row.barFraction * 100}%` }} />
                    </span>
                  )}
                </button>
              </li>
            )
          })}
        </ol>
      )}
      <p className="p-2 text-gray-600">
        {without === 1 ? '1 tramo sin impacto' : `${without} tramos sin impacto`}
      </p>
    </section>
  )
}
