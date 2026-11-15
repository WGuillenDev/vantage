import { Layers } from 'lucide-react'
import { useState } from 'react'
import { ALTERNATE_COLOR, CLOSED_COLOR, COMMUNITY_COLOR, HOSPITAL_COLOR } from './colors.ts'
import { colorForCriticality, GRAY, legendRange, rankingUnknown } from './mapCorridor.ts'
import type { ZoneData } from './zoneData.ts'

const Swatch = ({ color, dashed = false }: { color: string; dashed?: boolean }) =>
  dashed ? (
    <span aria-hidden="true" className="inline-block w-4 border-t-4 border-dashed" style={{ borderColor: color }} />
  ) : (
    <span aria-hidden="true" className="inline-block h-1 w-4 rounded" style={{ background: color }} />
  )

const Dot = ({ color }: { color: string }) => (
  <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full border border-white" style={{ background: color }} />
)

export function MapLegend({ data, hasClosed }: { data: ZoneData; hasClosed: boolean }) {
  // Collapsed on phones so it does not cover the map or the attribution.
  const [open, setOpen] = useState(() => window.matchMedia('(min-width: 768px)').matches)
  const { min, max } = legendRange(data.units)
  const format = new Intl.NumberFormat('es').format
  const range = { min, max }
  const gradient = [0, 0.25, 0.5, 0.75, 1].map((t) => colorForCriticality(min + (max - min) * t, range)).join(', ')

  return (
    <div className="absolute bottom-6 left-2 max-w-[calc(100%-4rem)] rounded-card bg-surface/90 text-xs shadow-card backdrop-blur" role="group" aria-label="Leyenda de criticidad">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-11 w-full items-center gap-1.5 px-2.5 font-semibold md:min-h-8"
      >
        <Layers aria-hidden="true" className="h-4 w-4" />
        Criticidad del tramo
      </button>
      {open && (
        <div className="space-y-1 px-2.5 pb-2">
          <div className="h-2 w-40 rounded" style={{ background: `linear-gradient(to right, ${gradient})` }} />
          <p className="flex w-40 justify-between tabular-nums">
            <span>{format(min)}</span>
            <span>{format(max)}</span>
          </p>
          {rankingUnknown(data.units) && <p className="w-40">El color no ordena los tramos: se desconoce la población.</p>}
          <p className="flex items-center gap-1.5">
            <Swatch color={GRAY} />
            sin impacto
          </p>
          {hasClosed && (
            <>
              <p className="flex items-center gap-1.5">
                <Swatch color={CLOSED_COLOR} dashed />
                tramo cerrado
              </p>
              <p className="flex items-center gap-1.5">
                <Swatch color={ALTERNATE_COLOR} dashed />
                rutas alternas
              </p>
            </>
          )}
          <p className="flex items-center gap-1.5">
            <Dot color={HOSPITAL_COLOR} />
            hospital de referencia
          </p>
          <p className="flex items-center gap-1.5">
            <Dot color={COMMUNITY_COLOR} />
            comunidad
          </p>
        </div>
      )}
    </div>
  )
}
