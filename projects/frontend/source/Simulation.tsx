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

  if (data === null) return <Message>Sin datos de la zona para simular.</Message>
  const view = simulationView(data.graph, data.units, data.baseline, closed)

  return (
    <section aria-label="Simulación de cierre" className="space-y-3 p-3 text-sm">
      <h2 className="font-semibold">Simulación de cierre</h2>
      {view.chips.length === 0 ? (
        <p className="rounded-lg border border-dashed border-line p-3 text-muted">
          Ningún tramo cerrado. Elige un tramo y pulsa «Simular cierre de este tramo».
        </p>
      ) : (
        <>
          <div className="flex items-start justify-between gap-2">
            <ul className="flex flex-wrap gap-1.5" aria-label="Tramos cerrados">
              {view.chips.map((chip) => (
                <li key={chip.id} className="flex items-center rounded-full bg-red-50 pl-3 text-red-900">
                  <span>{chip.label}</span>
                  <button
                    type="button"
                    aria-label={`Quitar ${chip.label}`}
                    onClick={() => openUnit(chip.id)}
                    className="inline-flex h-8 w-8 items-center justify-center rounded-full hover:bg-red-100 max-md:h-11 max-md:w-11"
                  >
                    <X aria-hidden="true" className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
            <Button variant="ghost" onClick={resetClosed}>
              <RotateCcw aria-hidden="true" className="h-4 w-4" />
              Restablecer
            </Button>
          </div>
          <dl className="grid grid-cols-2 gap-2">
            <Stat label="Tiempo extra" value={view.summary.extraTime} />
            <Stat label="Población afectada" value={view.summary.population} />
            <div className="col-span-2">
              <Stat label="Comunidades sin ruta al hospital de referencia" value={view.summary.withoutRoute} />
            </div>
          </dl>
          {view.summary.note && <p className="rounded-lg bg-amber-50 p-2 text-amber-900">{view.summary.note}</p>}
          {view.alternateEdgeIds.length > 0 && (
            <p className="text-muted">Rutas alternas resaltadas en el mapa por su nombre: no es el desvío que tomaría cada comunidad.</p>
          )}
          <h3 className="font-medium">Comunidades afectadas</h3>
          {view.rows.length === 0 ? (
            <p>Ninguna comunidad pierde tiempo ni la ruta con este cierre.</p>
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
