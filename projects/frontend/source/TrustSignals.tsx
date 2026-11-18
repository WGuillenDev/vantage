import { useState } from 'react'
import { ChevronDown, Info, TriangleAlert } from 'lucide-react'
import { NOTICE, REFERRAL_NOTE, UNVALIDATED_BANNER, attributionLines, isUnvalidated, readingPanel } from './trustSignals.ts'
import { readyData, type ZoneState } from './zoneData.ts'

export function TrustHeader({ state }: { state: ZoneState }) {
  const zone = readyData(state)?.zone
  const [open, setOpen] = useState(false)
  return (
    <div className="border-b border-amber-400/20 bg-amber-400/8 px-3 py-1.5 text-xs text-amber-100 md:text-sm">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <p className="flex min-w-0 flex-1 items-center gap-1.5 leading-tight md:flex-none">
          <Info aria-hidden="true" className="h-4 w-4 shrink-0 text-amber-300" />
          {NOTICE}
        </p>
        {isUnvalidated(zone) && (
          <>
            {/* Narrow screens: a short chip that opens the full banner. */}
            <button
              type="button"
              aria-expanded={open}
              aria-label={UNVALIDATED_BANNER}
              onClick={() => setOpen((value) => !value)}
              className="inline-flex min-h-11 shrink-0 items-center gap-1 rounded-full bg-red-500/15 px-2.5 font-medium text-red-200 ring-1 ring-inset ring-red-400/30 md:hidden"
            >
              <TriangleAlert aria-hidden="true" className="h-4 w-4" />
              Not validated
            </button>
            <p role="status" className={`${open ? 'flex' : 'hidden md:flex'} basis-full items-center gap-1.5 rounded-full bg-red-500/15 px-2.5 py-0.5 font-medium text-red-200 ring-1 ring-inset ring-red-400/30 md:basis-auto`}>
              <TriangleAlert aria-hidden="true" className="h-4 w-4 shrink-0" />
              {UNVALIDATED_BANNER}
            </p>
          </>
        )}
      </div>
    </div>
  )
}

export function TrustFooter({ state }: { state: ZoneState }) {
  const data = readyData(state)
  if (data === null) return null
  const panel = readingPanel(data.meta, data.graph)
  return (
    <footer className="border-t border-line bg-surface px-3 text-xs text-muted">
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center gap-1.5 py-2 font-medium text-ink max-md:min-h-11">
          <ChevronDown aria-hidden="true" className="h-4 w-4 transition-transform group-open:rotate-180" />
          How to read these numbers, and sources
        </summary>
        <div className="max-h-[40vh] space-y-3 overflow-y-auto pb-3">
          <ul className="list-disc space-y-0.5 pl-5">
            <li>
              Times use a constant speed per road class: {panel.speeds.map((s) => `${s.roadClass} ${s.kmh} km/h`).join(', ')}.
            </li>
            <li>Referral hospitals: {panel.hospitals.join(', ')}.</li>
            <li>{REFERRAL_NOTE}</li>
            {panel.radarNote && <li>Radar: {panel.radarNote}</li>}
            <li>“No route to the referral hospital” means there is no path to those hospitals.</li>
            <li>Population is a modelled estimate.</li>
            <li>OpenStreetMap quality varies.</li>
          </ul>
          <ul aria-label="Sources" className="space-y-0.5">
            {attributionLines(data.meta).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      </details>
    </footer>
  )
}
