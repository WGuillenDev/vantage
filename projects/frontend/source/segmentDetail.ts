import { formatDuration, formatPopulation } from './format.ts'
import { rowView, type RankedUnit } from './ranking.ts'
import { NO_ROUTE, suspectLabel } from './trustSignals.ts'

export { NO_ROUTE }
export const NO_DATA = 'sin dato'
export const HYPOTHESIS_LABEL = 'Hipótesis, no causa confirmada'
export const WHY_TEXT =
  'La lluvia reciente es contexto, no una predicción. No se probó como señal de cierres en esta zona.'
const WINDOW_DAYS = 12

interface PerCommunity {
  community_id: string
  time_s: number | null
  extra_s: number | null
  hospital_id: string | null
}

export interface DetailUnit extends RankedUnit {
  per_community?: PerCommunity[]
  alternates?: { name: string; vehicles: 'light' | 'freight' }[]
  exposure?: { rain_mm_12d: number | null } | null
  suspect_isolated_community_ids?: string[]
}

export interface BaselineEntry {
  community_id: string
  time_s: number | null
  hospital_id: string | null
}

export interface DetailGraph {
  edges: { id: string; road?: string | null }[]
  hospitals: { id: string; name: string }[]
  communities: { id: string; name: string }[]
}

export interface CommunityView {
  id: string
  name: string
  withoutClosure: string
  withClosure: string
  extra: string
  hospital: string
}

export interface DetailView {
  header: string
  rank: number
  extraTime: string
  population: string
  communities: CommunityView[]
  alternates: string[]
  rain: string
  rainLabel: string
}

const timeText = (seconds: number | null | undefined): string =>
  seconds === undefined ? NO_DATA : seconds === null ? NO_ROUTE : formatDuration(seconds)

const formatMm = (mm: number): string => String(Math.round(mm * 10) / 10).replace('.', ',')

export function detailView(unit: DetailUnit, graph: DetailGraph, baseline: BaselineEntry[]): DetailView {
  const names = new Map(graph.communities.map((c) => [c.id, c.name]))
  const hospitals = new Map(graph.hospitals.map((h) => [h.id, h.name]))
  const before = new Map(baseline.map((b) => [b.community_id, b.time_s]))
  const after = new Map((unit.per_community ?? []).map((p) => [p.community_id, p]))

  const communities = unit.affected_community_ids.map((id) => {
    const entry = after.get(id)
    const hospital = entry === undefined ? NO_DATA : entry.hospital_id === null ? NO_ROUTE : (hospitals.get(entry.hospital_id) ?? NO_DATA)
    return {
      isolated: entry !== undefined && entry.time_s === null,
      sortExtra: entry?.extra_s ?? 0,
      view: {
        id,
        name: names.get(id) ?? id,
        withoutClosure: timeText(before.get(id)),
        withClosure:
          entry?.time_s === null ? suspectLabel(id, unit.suspect_isolated_community_ids ?? []) : timeText(entry === undefined ? undefined : entry.time_s),
        extra: timeText(entry === undefined ? undefined : entry.extra_s),
        hospital,
      },
    }
  })
  communities.sort(
    (a, b) => Number(b.isolated) - Number(a.isolated) || b.sortExtra - a.sortExtra || a.view.id.localeCompare(b.view.id),
  )

  const alternates = (unit.alternates ?? []).map((a) => `${a.name} · ${a.vehicles === 'light' ? 'livianos' : 'pesados'}`)
  const mm = unit.exposure?.rain_mm_12d

  return {
    header: rowView(unit, graph.edges, 0).label,
    rank: unit.rank,
    extraTime: unit.extra_time_s === null ? NO_ROUTE : formatDuration(unit.extra_time_s),
    population: formatPopulation(unit.population_dependent),
    communities: communities.map((c) => c.view),
    alternates: alternates.length === 0 ? ['sin alternas registradas'] : alternates,
    rain: typeof mm === 'number' ? `${formatMm(mm)} mm en 12 días` : NO_DATA,
    rainLabel: HYPOTHESIS_LABEL,
  }
}

export interface RainDay {
  date: string
  mm: number
}

export const rainErrorMessage = (detail: string): string => `No se pudo cargar rain.csv: ${detail}.`

// Parses rain.csv (`date,precip_mm`); anything unreadable fails naming the file (INV-12).
export function parseRain(text: string): RainDay[] {
  const lines = text.trim().split(/\r?\n/)
  if (lines[0]?.trim() !== 'date,precip_mm') throw new Error(rainErrorMessage('encabezado inesperado'))
  const rows = lines.slice(1).map((line) => {
    const [date, value] = line.split(',')
    const mm = Number(value)
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date ?? '') || value === undefined || value.trim() === '' || !Number.isFinite(mm) || mm < 0) {
      throw new Error(rainErrorMessage(`fila no válida "${line}"`))
    }
    return { date: date!, mm }
  })
  if (rows.length === 0) throw new Error(rainErrorMessage('no tiene filas'))
  return rows
}

// The days of the window: the 12 ending at `end`, inclusive (INV-11).
export function highlightedDays(rows: RainDay[], end: string): (RainDay & { highlighted: boolean })[] {
  const last = Date.parse(`${end}T00:00:00Z`)
  const first = last - (WINDOW_DAYS - 1) * 86_400_000
  return rows.map((row) => {
    const time = Date.parse(`${row.date}T00:00:00Z`)
    return { ...row, highlighted: time >= first && time <= last }
  })
}

export async function loadRain(url: string): Promise<RainDay[]> {
  let response: Response
  try {
    response = await fetch(url)
  } catch {
    throw new Error(rainErrorMessage('sin conexión o archivo inaccesible'))
  }
  if (!response.ok) throw new Error(rainErrorMessage(`error ${response.status}`))
  return parseRain(await response.text())
}
