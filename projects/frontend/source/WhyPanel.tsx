import { useEffect, useState } from 'react'
import { HYPOTHESIS_LABEL, WHY_TEXT, highlightedDays, loadRain, type RainDay } from './segmentDetail.ts'
import { rainUrl } from './storage.ts'
import type { ZoneData } from './zoneData.ts'

const W = 300
const H = 100

function RainChart({ days }: { days: ReturnType<typeof highlightedDays> }) {
  const max = Math.max(1, ...days.map((d) => d.mm))
  const step = W / days.length
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Lluvia diaria del periodo, con los últimos 12 días resaltados" className="w-full">
      {days.map((d, i) => {
        const h = (d.mm / max) * (H - 4)
        return (
          <rect key={d.date} x={i * step} y={H - h} width={Math.max(1, step - 1)} height={h} fill={d.highlighted ? '#d97706' : '#9ca3af'}>
            <title>{`${d.date}: ${d.mm} mm`}</title>
          </rect>
        )
      })}
    </svg>
  )
}

export function WhyPanel({ data }: { data: ZoneData | string | null }) {
  const zoneId = typeof data === 'object' && data !== null ? data.zone.id : null
  const end = typeof data === 'object' && data !== null ? data.meta.rain?.end : undefined
  const [state, setState] = useState<{ zoneId: string; rows: RainDay[] | string } | null>(null)

  useEffect(() => {
    if (zoneId === null) return
    let cancelled = false
    loadRain(rainUrl(zoneId))
      .then((rows) => !cancelled && setState({ zoneId, rows }))
      .catch((reason: unknown) => !cancelled && setState({ zoneId, rows: reason instanceof Error ? reason.message : String(reason) }))
    return () => {
      cancelled = true
    }
  }, [zoneId])

  const current = state !== null && state.zoneId === zoneId ? state.rows : null
  return (
    <div className="p-2 text-sm">
      <p className="font-medium">{HYPOTHESIS_LABEL}</p>
      <p>{WHY_TEXT}</p>
      {current === null ? (
        <p>Cargando lluvia…</p>
      ) : typeof current === 'string' ? (
        <p role="alert">{current}</p>
      ) : end === undefined ? (
        <p role="alert">No se pudo cargar meta.json: falta el fin del periodo de lluvia.</p>
      ) : (
        <RainChart days={highlightedDays(current, end)} />
      )}
    </div>
  )
}
