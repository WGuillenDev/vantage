import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { legendRange, pointFeatures, unitFeatures, type CorridorGraph } from './mapCorridor.ts'
import type { RankedUnit } from './ranking.ts'

const examples = new URL('../../contract/examples/', import.meta.url)
const read = <T>(zone: string, file: string): T => JSON.parse(readFileSync(new URL(`${zone}/${file}`, examples), 'utf-8')) as T

describe.each(['mock-validated', 'mock-unvalidated'])('map-corridor adversarial: %s mock set', (zone) => {
  const graph = read<CorridorGraph>(zone, 'graph.json')
  const units = read<{ candidates: RankedUnit[] }>(zone, 'scenarios.json').candidates

  test('INV-04 every edge with a candidate_id of the zone is drawn, in exactly one feature', () => {
    const drawn = unitFeatures(graph, units).features
    const ids = new Set(units.map((unit) => unit.id))
    const expected = graph.edges.filter((edge) => edge.candidate_id !== null && ids.has(edge.candidate_id))
    expect(drawn.reduce((sum, feature) => sum + feature.geometry.coordinates.length, 0)).toBe(expected.length)
    expect(new Set(drawn.map((feature) => feature.properties.id)).size).toBe(drawn.length)
  })

  test('INV-04 every unit of scenarios.json owns at least one drawn edge', () => {
    const drawn = new Set(unitFeatures(graph, units).features.map((feature) => feature.properties.id))
    for (const unit of units) expect(drawn.has(unit.id)).toBe(true)
  })

  test('INV-08 every hospital and community of graph.json is drawn at a real node', () => {
    const points = pointFeatures(graph)
    expect(points.hospitals.features).toHaveLength(graph.hospitals.length)
    expect(points.communities.features).toHaveLength(graph.communities.length)
  })

  test('INV-07 the legend range covers every criticality of the units with an affected community', () => {
    const { min, max } = legendRange(units)
    for (const unit of units.filter((u) => u.affected_community_ids.length > 0)) {
      expect(unit.criticality).toBeGreaterThanOrEqual(min)
      expect(unit.criticality).toBeLessThanOrEqual(max)
    }
  })
})
