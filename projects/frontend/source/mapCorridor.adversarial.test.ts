import { describe, expect, test } from 'bun:test'
import { checkSchemaVersion, colorForCriticality, unitFeatures, type CorridorGraph } from './mapCorridor.ts'
import type { RankedUnit } from './ranking.ts'

describe('map-corridor adversarial: INV-12 trust boundary', () => {
  test('INV-12 a null body, a numeric version and a padded version are all rejected', () => {
    expect(() => checkSchemaVersion('meta.json', null)).toThrow(/meta\.json/)
    expect(() => checkSchemaVersion('meta.json', { schema_version: 0.3 })).toThrow(/meta\.json/)
    expect(() => checkSchemaVersion('meta.json', { schema_version: '0.3.1' })).toThrow(/meta\.json/)
    expect(() => checkSchemaVersion('meta.json', { schema_version: ' 0.3' })).toThrow(/meta\.json/)
  })
})

describe('map-corridor adversarial: color scale', () => {
  const valid = /^#[0-9a-f]{6}$/

  test('INV-06 values outside the range are clamped to the ends of the scale', () => {
    const range = { min: 10, max: 20 }
    expect(colorForCriticality(-5, range)).toBe(colorForCriticality(10, range))
    expect(colorForCriticality(99, range)).toBe(colorForCriticality(20, range))
  })

  test('INV-06 a single affected unit in a zone of one unit gets a valid color', () => {
    expect(colorForCriticality(5, { min: 5, max: 5 })).toMatch(valid)
  })
})

describe('map-corridor adversarial: unit grouping', () => {
  const unit = (id: string): RankedUnit => ({
    id,
    rank: 1,
    length_m: 1,
    edge_ids: [],
    criticality: 1,
    extra_time_s: null,
    population_dependent: null,
    affected_community_ids: ['c1'],
  })

  test('INV-04 units with no edges in the graph are not drawn and do not break the others', () => {
    const graph: CorridorGraph = {
      nodes: [],
      hospitals: [],
      communities: [],
      edges: [{ id: 'e1', from: 'a', to: 'b', time_s: 1, candidate_id: 'T-01', geometry: [[0, 0], [1, 1]] }],
    }
    const ids = unitFeatures(graph, [unit('T-01'), unit('T-02')]).features.map((f) => f.properties.id)
    expect(ids).toEqual(['T-01'])
  })
})
