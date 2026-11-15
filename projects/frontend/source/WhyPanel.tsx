import { useEffect, useState } from 'react'
import { HYPOTHESIS_LABEL, WHY_TEXT, highlightedDays, loadRain, type RainDay } from './segmentDetail.ts'
import { rainUrl } from './storage.ts'
import { Badge, Message } from './ui.tsx'
import type { ZoneState } from './zoneData.ts'

const W = 300
const H = 100
const HIGHLIGHT = '#d97706'
const BASE = '#94a3b8'

function RainChart({ days }: { days: ReturnType<typeof highlightedDays> }) {
  const max = Math.max(1, ...days.map((d) => d.mm))
  const step = W / days.length
  const first = days[0]?.date
  const last = days[days.length - 1]?.date
  return (
    <figure className="space-y-1">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Lluvia diaria del periodo, con los últimos 12 días resaltados" className="w-full rounded-lg bg-slate-50">
        {days.map((d, i) => {
          const h = (d.mm / max) * (H - 4)
          return (
            <rect key={d.date} x={i * step} y={H - h} width={Math.max(1, step - 1)} height={h} fill={d.highlighted ? HIGHLIGHT : BASE}>
              <title>{`${d.date}: ${d.mm} mm`}</title>
            </rect>
          )
        })}
      </svg>
      <figcaption className="flex justify-between text-xs text-muted tabular-nums">
        <span>{first}</span>
        <span>máx. {Math.round(max)} mm/día</span>
        <span>{last}</span>
      </figcaption>
      <p className="flex items-center gap-3 text-xs text-muted">
        <span className="flex items-center gap-1">
          <span aria-hidden="true" className="h-2 w-3 rounded-sm" style={{ background: HIGHLIGHT }} />
          últimos 12 días
        </span>
        <span className="flex items-center gap-1">
          <span aria-hidden="true" className="h-2 w-3 rounded-sm" style={{ background: BASE }} />
          resto del periodo
        </span>
      </p>
    </figure>
  )
}

export default function WhyPanel({ state }: { state: ZoneState }) {
  const zoneId = state.status === 'ready' ? state.data.zone.id : null
  const end = state.status === 'ready' ? state.data.meta.rain?.end : undefined
  const [loaded, setLoaded] = useState<{ zoneId: string; rows: RainDay[] | string } | null>(null)

  useEffect(() => {
    if (zoneId === null) return
    let cancelled = false
    loadRain(rainUrl(zoneId))
      .then((rows) => !cancelled && setLoaded({ zoneId, rows }))
      .catch((reason: unknown) => !cancelled && setLoaded({ zoneId, rows: reason instanceof Error ? reason.message : String(reason) }))
    return () => {
      cancelled = true
    }
  }, [zoneId])

  const current = loaded !== null && loaded.zoneId === zoneId ? loaded.rows : null
  return (
    <div className="space-y-3 p-3 text-sm">
      <Badge tone="warning">{HYPOTHESIS_LABEL}</Badge>
      <p>{WHY_TEXT}</p>
      {current === null ? (
        <p className="text-muted">Cargando lluvia…</p>
      ) : typeof current === 'string' ? (
        <Message alert>{current}</Message>
      ) : end === undefined ? (
        <Message alert>No se pudo cargar meta.json: falta el fin del periodo de lluvia.</Message>
      ) : (
        <RainChart days={highlightedDays(current, end)} />
      )}
    </div>
  )
}
