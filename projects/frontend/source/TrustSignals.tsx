import { ChevronDown, Info, TriangleAlert } from 'lucide-react'
import { NOTICE, REFERRAL_NOTE, UNVALIDATED_BANNER, attributionLines, isUnvalidated, readingPanel } from './trustSignals.ts'
import { readyData, type ZoneState } from './zoneData.ts'

export function TrustHeader({ state }: { state: ZoneState }) {
  const zone = readyData(state)?.zone
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-950 md:text-sm">
      <p className="flex items-center gap-1.5">
        <Info aria-hidden="true" className="h-4 w-4 shrink-0" />
        {NOTICE}
      </p>
      {isUnvalidated(zone) && (
        <p role="status" className="flex items-center gap-1.5 rounded-full bg-red-100 px-2.5 py-0.5 font-medium text-red-900">
          <TriangleAlert aria-hidden="true" className="h-4 w-4 shrink-0" />
          {UNVALIDATED_BANNER}
        </p>
      )}
    </div>
  )
}

export function TrustFooter({ state }: { state: ZoneState }) {
  const data = readyData(state)
  if (data === null) return null
  const panel = readingPanel(data.meta, data.graph)
  return (
    <footer className="border-t border-line bg-white px-3 text-xs text-muted">
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center gap-1.5 py-2 font-medium text-ink max-md:min-h-11">
          <ChevronDown aria-hidden="true" className="h-4 w-4 transition-transform group-open:rotate-180" />
          Cómo leer estos números y fuentes
        </summary>
        <div className="max-h-[40vh] space-y-3 overflow-y-auto pb-3">
          <ul className="list-disc space-y-0.5 pl-5">
            <li>
              Los tiempos usan una velocidad constante por clase de vía: {panel.speeds.map((s) => `${s.roadClass} ${s.kmh} km/h`).join(', ')}.
            </li>
            <li>Hospitales de referencia: {panel.hospitals.join(', ')}.</li>
            <li>{REFERRAL_NOTE}</li>
            {panel.radarNote && <li>Radar: {panel.radarNote}</li>}
            <li>«Sin ruta al hospital de referencia» significa que no hay camino a esos hospitales.</li>
            <li>La población es una estimación modelada.</li>
            <li>La calidad de OpenStreetMap varía.</li>
          </ul>
          <ul aria-label="Fuentes" className="space-y-0.5">
            {attributionLines(data.meta).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      </details>
    </footer>
  )
}
