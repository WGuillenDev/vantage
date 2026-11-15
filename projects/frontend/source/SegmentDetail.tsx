import { useAppStore } from './store.ts'
import { detailView } from './segmentDetail.ts'
import type { ZoneData } from './zoneData.ts'

export function SegmentDetail({ data, onWhy }: { data: ZoneData | string | null; onWhy?: () => void }) {
  const selected = useAppStore((state) => state.selectedUnitId)
  const closeUnit = useAppStore((state) => state.closeUnit)
  if (typeof data !== 'object' || data === null || selected === null) return null
  const unit = data.units.find((item) => item.id === selected)
  if (!unit) return null
  const view = detailView(unit, data.graph, data.baseline)

  return (
    <section aria-label="Detalle del tramo" className="border-b p-2 text-sm">
      <h2 className="font-semibold">{view.header}</h2>
      <p>Posición {view.rank}</p>
      <p>
        Tiempo extra: {view.extraTime} · Población que depende: {view.population}
      </p>
      <h3 className="mt-2 font-medium">Comunidades afectadas</h3>
      <ul className="list-disc pl-5">
        {view.communities.map((c) => (
          <li key={c.id}>
            <span className="font-medium">{c.name}</span>: sin cierre {c.withoutClosure}, con cierre {c.withClosure}, extra {c.extra}. Hospital: {c.hospital}
          </li>
        ))}
      </ul>
      <h3 className="mt-2 font-medium">Alternas</h3>
      <ul className="list-disc pl-5">
        {view.alternates.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
      <h3 className="mt-2 font-medium">Exposición</h3>
      <p>
        Lluvia: {view.rain} <em className="text-gray-700">({view.rainLabel})</em>
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
        <button type="button" onClick={() => closeUnit(unit.id)} className="rounded border px-3 py-1 max-md:min-h-11">
          Simular cierre de este tramo
        </button>
        {onWhy && (
          <button type="button" onClick={onWhy} className="rounded border px-3 py-1 md:hidden max-md:min-h-11">
            ¿Por qué?
          </button>
        )}
      </div>
    </section>
  )
}
