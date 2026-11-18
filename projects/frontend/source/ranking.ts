import { formatDuration, formatPopulation } from './format.ts'
import { NO_ROUTE } from './trustSignals.ts'

export interface RankedUnit {
  id: string
  rank: number
  length_m: number
  edge_ids: string[]
  criticality: number
  extra_time_s: number | null
  population_dependent: number | null
  affected_community_ids: string[]
}

export interface RowView {
  id: string
  label: string
  length: string
  extraTime: string
  population: string
  barFraction: number | null
}

export const listedUnits = (units: RankedUnit[]): RankedUnit[] =>
  units.filter((unit) => unit.affected_community_ids.length > 0).sort((a, b) => a.rank - b.rank)

export const countWithoutImpact = (units: RankedUnit[]): number =>
  units.filter((unit) => unit.affected_community_ids.length === 0).length

export const maxCriticality = (units: RankedUnit[]): number => Math.max(0, ...units.map((unit) => unit.criticality))

export const noPopulationNote = (units: RankedUnit[]): boolean => maxCriticality(units) === 0

// Ties go to the road met first along the unit's edges.
function mainRoad(unit: RankedUnit, edges: { id: string; road?: string | null }[]): string {
  const roadById = new Map(edges.map((edge) => [edge.id, edge.road]))
  const counts = new Map<string, number>()
  for (const id of unit.edge_ids) {
    const road = roadById.get(id)
    if (road) counts.set(road, (counts.get(road) ?? 0) + 1)
  }
  let best = 'Unnamed road'
  let bestCount = 0
  for (const [road, count] of counts) {
    if (count > bestCount) [best, bestCount] = [road, count]
  }
  return best
}

const formatLength = (meters: number): string =>
  Math.round(meters) < 1000 ? `${Math.round(meters)} m` : `${(meters / 1000).toFixed(1)} km`

export function rowView(unit: RankedUnit, edges: { id: string; road?: string | null }[], maxCrit: number): RowView {
  return {
    id: unit.id,
    label: `${mainRoad(unit, edges)} · ${unit.id}`,
    length: formatLength(unit.length_m),
    extraTime: unit.extra_time_s === null ? NO_ROUTE : formatDuration(unit.extra_time_s),
    population: formatPopulation(unit.population_dependent),
    barFraction: maxCrit > 0 ? unit.criticality / maxCrit : null,
  }
}

export type RankFilter = 'all' | 'no-route' | 'suspect'

const plain = (text: string): string => text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()

// The list the person narrows down: by text over the row label, and by a kind of unit.
export function filterUnits<T extends RankedUnit & { suspect_isolated_community_ids?: string[] }>(
  units: T[],
  edges: { id: string; road?: string | null }[],
  query: string,
  filter: RankFilter,
): T[] {
  const needle = plain(query.trim())
  return units.filter((unit) => {
    if (filter === 'no-route' && unit.extra_time_s !== null) return false
    if (filter === 'suspect' && (unit.suspect_isolated_community_ids ?? []).length === 0) return false
    return needle === '' || plain(rowView(unit, edges, 0).label).includes(needle)
  })
}
