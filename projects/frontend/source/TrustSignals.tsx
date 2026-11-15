import { NOTICE, REFERRAL_NOTE, UNVALIDATED_BANNER, attributionLines, isUnvalidated, readingPanel } from './trustSignals.ts'
import type { ZoneData } from './zoneData.ts'

export function TrustHeader({ data }: { data: ZoneData | string | null }) {
  const zone = typeof data === 'object' && data !== null ? data.zone : undefined
  return (
    <div className="text-sm">
      <p className="bg-amber-50 px-3 py-1 text-gray-900">{NOTICE}</p>
      {isUnvalidated(zone) && (
        <p role="status" className="bg-red-100 px-3 py-1 text-red-900">
          {UNVALIDATED_BANNER}
        </p>
      )}
    </div>
  )
}

export function TrustFooter({ data }: { data: ZoneData | string | null }) {
  if (typeof data !== 'object' || data === null) return null
  const panel = readingPanel(data.meta, data.graph)
  return (
    <footer className="border-t bg-white px-3 py-1 text-xs text-gray-700">
      <details>
        <summary className="flex cursor-pointer items-center max-md:min-h-11">Cómo leer estos números</summary>
        <ul className="list-disc pl-5">
          <li>
            Los tiempos usan una velocidad constante por clase de vía:{' '}
            {panel.speeds.map((s) => `${s.roadClass} ${s.kmh} km/h`).join(', ')}.
          </li>
          <li>Hospitales de referencia: {panel.hospitals.join(', ')}.</li>
          <li>{REFERRAL_NOTE}</li>
          {panel.radarNote && <li>Radar: {panel.radarNote}</li>}
          <li>«Sin ruta al hospital de referencia» significa que no hay camino a esos hospitales.</li>
          <li>La población es una estimación modelada.</li>
          <li>La calidad de OpenStreetMap varía.</li>
        </ul>
      </details>
      <ul className="mt-1">
        {attributionLines(data.meta).map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </footer>
  )
}
