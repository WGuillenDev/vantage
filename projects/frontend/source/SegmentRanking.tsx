import { Clock, Ruler, Search, Users } from 'lucide-react'
import { useState } from 'react'
import { colorForCriticality, legendRange, rankingUnknown, GRAY } from './mapCorridor.ts'
import { countWithoutImpact, filterUnits, listedUnits, maxCriticality, noPopulationNote, rowView, type RankFilter } from './ranking.ts'
import { useAppStore } from './store.ts'
import { ZoneGate } from './ZoneGate.tsx'
import type { ZoneState } from './zoneData.ts'

const FILTERS: { id: RankFilter; label: string }[] = [
  { id: 'all', label: 'All' },
  { id: 'no-route', label: 'No route' },
  { id: 'suspect', label: 'With suspects' },
]

export function SegmentRanking({ state }: { state: ZoneState }) {
  const selected = useAppStore((s) => s.selectedUnitId)
  const selectUnit = useAppStore((s) => s.selectUnit)
  const hoverUnit = useAppStore((s) => s.hoverUnit)
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<RankFilter>('all')

  return (
    <ZoneGate state={state}>
      {(data) => {
        const listed = listedUnits(data.units)
        const rows = filterUnits(listed, data.graph.edges, query, filter)
        const maxCrit = maxCriticality(data.units)
        const range = legendRange(data.units)
        const colored = !rankingUnknown(data.units)
        const without = countWithoutImpact(data.units)
        return (
          <section className="text-sm" aria-label="Critical segments">
            <div className="sticky top-0 z-10 space-y-2 border-b border-line bg-surface p-3">
              <h2 className="font-semibold">Critical segments by criticality</h2>
              {selected === null && <p className="text-muted">Tap a segment to see its affected communities and simulate its closure.</p>}
              {noPopulationNote(data.units) && (
                <p className="text-muted">The order comes from the extra time and the isolated communities, because population is unknown.</p>
              )}
              <label className="relative block">
                <span className="sr-only">Search segment</span>
                <Search aria-hidden="true" className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted" />
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search by road or code"
                  className="w-full rounded-lg border border-line bg-raised py-2 pl-8 pr-2 text-ink placeholder:text-slate-400 focus:border-brand/60 max-md:min-h-11"
                />
              </label>
              <div role="group" aria-label="Filter segments" className="flex flex-wrap gap-1">
                {FILTERS.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    aria-pressed={filter === item.id}
                    onClick={() => setFilter(item.id)}
                    className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors max-md:min-h-11 ${filter === item.id ? 'border-brand/60 bg-brand-soft text-brand-strong' : 'border-line text-muted hover:bg-white/5'}`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
            {listed.length === 0 ? (
              <p className="p-3">No segment leaves communities with extra time or without a route.</p>
            ) : rows.length === 0 ? (
              <p className="p-3 text-muted">No segment matches the search.</p>
            ) : (
              <ol className="divide-y divide-line">
                {rows.map((unit) => {
                  const row = rowView(unit, data.graph.edges, maxCrit)
                  const isSelected = unit.id === selected
                  return (
                    <li key={unit.id}>
                      <button
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => selectUnit(unit.id)}
                        onMouseEnter={() => hoverUnit(unit.id)}
                        onMouseLeave={() => hoverUnit(null)}
                        onFocus={() => hoverUnit(unit.id)}
                        onBlur={() => hoverUnit(null)}
                        className={`flex w-full items-stretch gap-3 px-3 py-2.5 text-left transition-colors max-md:min-h-11 ${isSelected ? 'bg-brand-soft shadow-[inset_2px_0_0_var(--color-brand)]' : 'hover:bg-white/5'}`}
                      >
                        <span
                          aria-hidden="true"
                          className="w-1 shrink-0 rounded-full"
                          style={{ background: colored ? colorForCriticality(unit.criticality, range) : GRAY }}
                        />
                        <span className="min-w-0 flex-1">
                          <span className="flex items-baseline justify-between gap-2">
                            <span className="truncate font-medium">{row.label}</span>
                            <span className="shrink-0 text-xs text-muted tabular-nums">#{unit.rank}</span>
                          </span>
                          <span className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted">
                            <span className="inline-flex items-center gap-1">
                              <Ruler aria-hidden="true" className="h-3 w-3" />
                              {row.length}
                            </span>
                            <span className="inline-flex items-center gap-1">
                              <Clock aria-hidden="true" className="h-3 w-3" />
                              {row.extraTime}
                            </span>
                            <span className="inline-flex items-center gap-1">
                              <Users aria-hidden="true" className="h-3 w-3" />
                              {row.population}
                            </span>
                          </span>
                          {row.barFraction !== null && (
                            <span className="mt-1.5 block h-1.5 overflow-hidden rounded-full bg-white/10" aria-hidden="true">
                              <span className="block h-full rounded-full bg-brand" style={{ width: `${row.barFraction * 100}%` }} />
                            </span>
                          )}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ol>
            )}
            <p className="border-t border-line p-3 text-muted">{without === 1 ? '1 segment with no impact' : `${without} segments with no impact`}</p>
          </section>
        )
      }}
    </ZoneGate>
  )
}
