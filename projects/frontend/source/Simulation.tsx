import { simulationView } from './closureWhatif.ts'
import { useAppStore } from './store.ts'
import type { ZoneData } from './zoneData.ts'

export function Simulation({ data }: { data: ZoneData | string | null }) {
  const closed = useAppStore((state) => state.closedUnitIds)
  const openUnit = useAppStore((state) => state.openUnit)
  const resetClosed = useAppStore((state) => state.resetClosed)

  if (typeof data !== 'object' || data === null) return <p className="p-3 text-sm">Sin datos de la zona para simular.</p>
  const view = simulationView(data.graph, data.units, data.baseline, closed)
  const touch = 'rounded border px-3 py-1 max-md:min-h-11 max-md:min-w-11'

  return (
    <section aria-label="Simulación de cierre" className="p-2 text-sm">
      <h2 className="font-semibold">Simulación de cierre</h2>
      {view.chips.length === 0 ? (
        <p className="mt-1">Ningún tramo cerrado. Elige un tramo y pulsa «Simular cierre de este tramo».</p>
      ) : (
        <>
          <ul className="mt-1 flex flex-wrap gap-1" aria-label="Tramos cerrados">
            {view.chips.map((chip) => (
              <li key={chip.id} className="flex items-center gap-1 rounded bg-gray-100 pl-2">
                <span>{chip.label}</span>
                <button type="button" aria-label={`Quitar ${chip.label}`} onClick={() => openUnit(chip.id)} className={touch}>
                  ×
                </button>
              </li>
            ))}
          </ul>
          <button type="button" onClick={resetClosed} className={`mt-2 ${touch}`}>
            Restablecer
          </button>
          <dl className="mt-2">
            <dt className="font-medium">Tiempo extra</dt>
            <dd>{view.summary.extraTime}</dd>
            <dt className="font-medium">Comunidades sin ruta al hospital de referencia</dt>
            <dd>{view.summary.withoutRoute}</dd>
            <dt className="font-medium">Población afectada</dt>
            <dd>{view.summary.population}</dd>
          </dl>
          {view.summary.note && <p className="mt-1">{view.summary.note}</p>}
          {view.alternateEdgeIds.length > 0 && (
            <p className="mt-1 text-gray-700">
              Rutas alternas resaltadas en el mapa por su nombre: no es el desvío que tomaría cada comunidad.
            </p>
          )}
          <h3 className="mt-2 font-medium">Comunidades afectadas</h3>
          {view.rows.length === 0 ? (
            <p>Ninguna comunidad pierde tiempo ni la ruta con este cierre.</p>
          ) : (
            <ul className="list-disc pl-5">
              {view.rows.map((row) => (
                <li key={row.id}>
                  <span className="font-medium">{row.name}</span>: sin cierre {row.withoutClosure}, con cierre {row.withClosure}, extra{' '}
                  {row.extra}. Hospital: {row.hospital}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  )
}
