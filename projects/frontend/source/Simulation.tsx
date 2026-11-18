import { RotateCcw, X } from 'lucide-react'
import { CommunityRow } from './CommunityRow.tsx'
import { simulationView } from './closureWhatif.ts'
import { useAppStore } from './store.ts'
import { Button, Message, Stat } from './ui.tsx'
import { readyData, type ZoneState } from './zoneData.ts'

export function Simulation({ state }: { state: ZoneState }) {
  const closed = useAppStore((s) => s.closedUnitIds)
  const openUnit = useAppStore((s) => s.openUnit)
  const resetClosed = useAppStore((s) => s.resetClosed)
  const data = readyData(state)

  if (data === null) return <Message>No zone data to simulate.</Message>
  const view = simulationView(data.graph, data.units, data.baseline, closed)

  return (
    <section aria-label="Closure simulation" className="space-y-3 p-3 text-sm">
      <h2 className="font-semibold">Closure simulation</h2>
      {view.chips.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line bg-raised/50 p-3 text-muted">
          No segment closed. Pick a segment and press “Simulate closing this segment”.
        </p>
      ) : (
        <>
          <div className="flex items-start justify-between gap-2">
            <ul className="flex flex-wrap gap-1.5" aria-label="Closed segments">
              {view.chips.map((chip) => (
                <li key={chip.id} className="flex items-center rounded-full bg-red-500/15 pl-3 text-red-200 ring-1 ring-inset ring-red-400/30">
                  <span>{chip.label}</span>
                  <button
                    type="button"
                    aria-label={`Remove ${chip.label}`}
                    onClick={() => openUnit(chip.id)}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full hover:bg-red-500/25 max-md:h-11 max-md:w-11"
                  >
                    <X aria-hidden="true" className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
            <Button variant="ghost" onClick={resetClosed}>
              <RotateCcw aria-hidden="true" className="h-4 w-4" />
              Reset
            </Button>
          </div>
          <dl className="grid grid-cols-2 gap-2">
            <Stat label="Extra time" value={view.summary.extraTime} />
            <Stat label="Affected population" value={view.summary.population} />
            <div className="col-span-2">
              <Stat label="Communities without a route to the referral hospital" value={view.summary.withoutRoute} />
            </div>
          </dl>
          {view.summary.note && <p className="rounded-lg border border-amber-400/25 bg-amber-400/10 p-2 text-amber-100">{view.summary.note}</p>}
          {view.alternateEdgeIds.length > 0 && (
            <p className="text-muted">Alternate routes highlighted on the map by name: not the detour each community would take.</p>
          )}
          <h3 className="font-medium">Affected communities</h3>
          {view.rows.length === 0 ? (
            <p>No community loses time or its route with this closure.</p>
          ) : (
            <ul className="space-y-1.5">
              {view.rows.map((row) => (
                <CommunityRow key={row.id} row={row} />
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  )
}
