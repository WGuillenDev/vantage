import type { RankedUnit } from './ranking.ts'

export const SCHEMA_VERSION = '0.3'
export const GRAY = '#9ca3af'

type Position = [number, number]
export type Bounds = [west: number, south: number, east: number, north: number]

export interface CorridorGraph {
  schema_version?: string
  nodes: { id: string; lon: number; lat: number }[]
  edges: {
    id: string
    from: string
    to: string
    time_s: number
    road?: string | null
    candidate_id: string | null
    geometry: Position[]
  }[]
  hospitals: { id: string; name: string; node: string }[]
  communities: { id: string; name: string; node: string }[]
}

interface Feature<G, P> {
  type: 'Feature'
  geometry: G
  properties: P
}
interface Collection<F> {
  type: 'FeatureCollection'
  features: F[]
}
type UnitFeature = Feature<{ type: 'MultiLineString'; coordinates: Position[][] }, { id: string; color: string; affected: boolean }>
type PointFeature = Feature<{ type: 'Point'; coordinates: Position }, { id: string; name: string }>

export const fileErrorMessage = (file: string, detail: string): string => `No se pudo cargar ${file}: ${detail}.`

export function checkSchemaVersion(file: string, data: unknown): void {
  const version = (data as { schema_version?: unknown } | null)?.schema_version
  if (version !== SCHEMA_VERSION) {
    throw new Error(fileErrorMessage(file, `versión de esquema no compatible (se esperaba ${SCHEMA_VERSION})`))
  }
}

// Viridis-like, color-blind safe; the most critical units are the darkest so they keep contrast on the light base map.
const RAMP = ['#fde725', '#5ec962', '#21918c', '#3b528b', '#440154']

const toRgb = (hex: string): number[] => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
const toHex = (rgb: number[]): string => `#${rgb.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')}`

export function colorForCriticality(value: number, range: { min: number; max: number }): string {
  const span = range.max - range.min
  const raw = span > 0 ? Math.min(1, Math.max(0, (value - range.min) / span)) : 0
  const t = Number.isNaN(raw) ? 0 : raw // a malformed criticality must not stop the map
  const scaled = t * (RAMP.length - 1)
  const index = Math.min(RAMP.length - 2, Math.floor(scaled))
  const from = toRgb(RAMP[index]!)
  const to = toRgb(RAMP[index + 1]!)
  return toHex(from.map((channel, i) => channel + (to[i]! - channel) * (scaled - index)))
}

const withCommunity = (units: RankedUnit[]): RankedUnit[] => units.filter((unit) => unit.affected_community_ids.length > 0)

// The scale spans only the units that are colored by it (INV-07).
export function legendRange(units: RankedUnit[]): { min: number; max: number } {
  const values = withCommunity(units).map((unit) => unit.criticality)
  if (values.length === 0) return { min: 0, max: 0 }
  return { min: Math.min(...values), max: Math.max(...values) }
}

// INV-16: with no population every criticality is 0, so the color says nothing about the order.
export function rankingUnknown(units: RankedUnit[]): boolean {
  const affected = withCommunity(units)
  return affected.length > 0 && affected.every((unit) => unit.criticality === 0)
}

export function unitFeatures(graph: CorridorGraph, units: RankedUnit[]): Collection<UnitFeature> {
  const range = legendRange(units)
  const byId = new Map(units.map((unit) => [unit.id, unit]))
  const lines = new Map<string, Position[][]>()
  for (const edge of graph.edges) {
    if (edge.candidate_id === null || !byId.has(edge.candidate_id)) continue
    const group = lines.get(edge.candidate_id)
    if (group) group.push(edge.geometry)
    else lines.set(edge.candidate_id, [edge.geometry])
  }
  const features = [...lines].map(([id, coordinates]): UnitFeature => {
    const unit = byId.get(id)!
    const affected = unit.affected_community_ids.length > 0
    return {
      type: 'Feature',
      geometry: { type: 'MultiLineString', coordinates },
      properties: { id, affected, color: affected ? colorForCriticality(unit.criticality, range) : GRAY },
    }
  })
  return { type: 'FeatureCollection', features }
}

export function pointFeatures(graph: CorridorGraph): {
  hospitals: Collection<PointFeature>
  communities: Collection<PointFeature>
} {
  const position = new Map(graph.nodes.map((node) => [node.id, [node.lon, node.lat] as Position]))
  const collect = (items: { id: string; name: string; node: string }[]): Collection<PointFeature> => ({
    type: 'FeatureCollection',
    features: items.flatMap((item) => {
      const coordinates = position.get(item.node)
      return coordinates
        ? [{ type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates }, properties: { id: item.id, name: item.name } }]
        : []
    }),
  })
  return { hospitals: collect(graph.hospitals), communities: collect(graph.communities) }
}

export const fitBounds = ([west, south, east, north]: Bounds): [Position, Position] => [
  [west, south],
  [east, north],
]
