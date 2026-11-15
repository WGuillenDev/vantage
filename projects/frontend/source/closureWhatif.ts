import { formatDuration, formatPopulation } from './format.ts'
import { computeAccess } from './graph.ts'
import { unitFeatures, type CorridorGraph } from './mapCorridor.ts'
import { rowView } from './ranking.ts'
import { NO_DATA, NO_ROUTE, type BaselineEntry, type DetailUnit } from './segmentDetail.ts'
import { simulationNote } from './trustSignals.ts'

export interface AffectedRow {
  communityId: string
  name: string
  population: number | null
  beforeSeconds: number
  afterSeconds: number | null
  extraSeconds: number | null
  hospitalId: string | null
}

export interface Simulation {
  rows: AffectedRow[]
  extraTime_s: number | null
  withoutRoute: number
  population: number | null
}

const idNumber = (id: string): number => Number(id.replace(/\D/g, ''))

// The edges removed when these units are closed: the union of their edge_ids. A unit the zone does not list adds none.
export function closedEdgeIds(units: DetailUnit[], closedIds: readonly string[]): string[] {
  const byId = new Map(units.map((unit) => [unit.id, unit]))
  const edges = new Set<string>()
  for (const id of closedIds) for (const edge of byId.get(id)?.edge_ids ?? []) edges.add(edge)
  return [...edges]
}

// Affected: it had a route in the baseline and, with the closure, has none or a longer one.
export function simulate(graph: CorridorGraph, units: DetailUnit[], baseline: BaselineEntry[], closedIds: readonly string[]): Simulation {
  const before = new Map(baseline.map((entry) => [entry.community_id, entry.time_s]))
  const communities = new Map(graph.communities.map((community) => [community.id, community]))
  const rows: AffectedRow[] = []
  for (const access of computeAccess(graph, closedEdgeIds(units, closedIds))) {
    const base = before.get(access.community_id)
    if (base === null || base === undefined) continue
    if (access.time_s !== null && access.time_s <= base) continue
    const community = communities.get(access.community_id)!
    rows.push({
      communityId: access.community_id,
      name: community.name,
      population: community.population ?? null,
      beforeSeconds: base,
      afterSeconds: access.time_s,
      extraSeconds: access.time_s === null ? null : access.time_s - base,
      hospitalId: access.hospital_id,
    })
  }
  // Without a route first, then the longest extra time, then by community number.
  rows.sort(
    (a, b) =>
      Number(b.afterSeconds === null) - Number(a.afterSeconds === null) ||
      (b.extraSeconds ?? 0) - (a.extraSeconds ?? 0) ||
      idNumber(a.communityId) - idNumber(b.communityId),
  )
  const extra = rows.flatMap((row) => (row.extraSeconds === null ? [] : [row.extraSeconds]))
  const known = rows.flatMap((row) => (row.population === null ? [] : [row.population]))
  return {
    rows,
    extraTime_s: extra.length === 0 ? null : Math.max(...extra),
    withoutRoute: rows.length - extra.length,
    population: known.length === 0 ? null : known.reduce((sum, value) => sum + value, 0),
  }
}

// Alternate roads are named, not routed: the names listed by the closed units.
export function alternateRoads(units: DetailUnit[], closedIds: readonly string[]): string[] {
  const byId = new Map(units.map((unit) => [unit.id, unit]))
  const names = new Set<string>()
  for (const id of closedIds) for (const alternate of byId.get(id)?.alternates ?? []) names.add(alternate.name)
  return [...names]
}

export const alternateEdgeIds = (edges: { id: string; road?: string | null }[], names: readonly string[]): string[] =>
  edges.filter((edge) => edge.road != null && names.includes(edge.road)).map((edge) => edge.id)

// Map data (INV-12): the closed units in the closed style, and the alternate edges as plain lines.
export function closedFeatures(graph: CorridorGraph, units: DetailUnit[], closedIds: readonly string[]) {
  const closed = new Set(closedIds)
  const { features } = unitFeatures(graph, units)
  return { type: 'FeatureCollection' as const, features: features.filter((feature) => closed.has(feature.properties.id)) }
}

export function alternateFeatures(edges: CorridorGraph['edges'], ids: readonly string[]) {
  const wanted = new Set(ids)
  return {
    type: 'FeatureCollection' as const,
    features: edges
      .filter((edge) => wanted.has(edge.id))
      .map((edge) => ({
        type: 'Feature' as const,
        geometry: { type: 'LineString' as const, coordinates: edge.geometry },
        properties: { id: edge.id },
      })),
  }
}

export function simulationView(graph: CorridorGraph, units: DetailUnit[], baseline: BaselineEntry[], closedIds: readonly string[]) {
  const listed = new Set(units.map((unit) => unit.id))
  const ids = closedIds.filter((id) => listed.has(id))
  const sim = simulate(graph, units, baseline, ids)
  const hospitals = new Map(graph.hospitals.map((hospital) => [hospital.id, hospital.name]))
  const byId = new Map(units.map((unit) => [unit.id, unit]))
  return {
    chips: ids.map((id) => ({ id, label: rowView(byId.get(id)!, graph.edges, 0).label })),
    summary: {
      extraTime: sim.extraTime_s === null ? 'ninguno' : formatDuration(sim.extraTime_s),
      withoutRoute: sim.withoutRoute,
      population: formatPopulation(sim.population),
      note: simulationNote(sim.withoutRoute),
    },
    rows: sim.rows.map((row) => ({
      id: row.communityId,
      name: row.name,
      withoutClosure: formatDuration(row.beforeSeconds),
      withClosure: row.afterSeconds === null ? NO_ROUTE : formatDuration(row.afterSeconds),
      extra: row.extraSeconds === null ? NO_ROUTE : formatDuration(row.extraSeconds),
      hospital: row.hospitalId === null ? NO_ROUTE : (hospitals.get(row.hospitalId) ?? NO_DATA),
    })),
    closedEdgeIds: closedEdgeIds(units, ids),
    alternateEdgeIds: alternateEdgeIds(graph.edges, alternateRoads(units, ids)),
  }
}
