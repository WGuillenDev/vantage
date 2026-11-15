import { afterEach, describe, expect, test } from 'bun:test'
import { loadAreas, loadZoneFile } from './storage.ts'
import { checkSchemaVersion, colorForCriticality, unitFeatures, type CorridorGraph } from './mapCorridor.ts'
import type { RankedUnit } from './ranking.ts'

const realFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = realFetch
})
const respondWith = (response: object) => {
  globalThis.fetch = (async () => response) as unknown as typeof fetch
}
const respondJson = (body: unknown) => respondWith({ ok: true, status: 200, json: async () => body })

describe('map-corridor adversarial: INV-12 trust boundary', () => {
  test('INV-12 a 200 response that is not JSON (dev server HTML fallback) names the file in Spanish', async () => {
    respondWith({
      ok: true,
      status: 200,
      json: async () => {
        throw new SyntaxError("Unexpected token '<'")
      },
    })
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/No se pudo cargar graph\.json/)
  })

  test('INV-12 areas.json with a valid version but no "areas" list is rejected, not returned as undefined', async () => {
    respondJson({ schema_version: '0.3' })
    await expect(loadAreas()).rejects.toThrow(/areas\.json/)
  })

  test('INV-12 a zone file missing its required lists is rejected naming the file', async () => {
    const cases: [string, Record<string, unknown>][] = [
      ['scenarios.json', { schema_version: '0.3', baseline: [] }],
      ['scenarios.json', { schema_version: '0.3', candidates: 'x' }],
      ['graph.json', { schema_version: '0.3', nodes: [], edges: [], hospitals: [] }],
    ]
    for (const [file, body] of cases) {
      respondJson(body)
      await expect(loadZoneFile('z', file)).rejects.toThrow(new RegExp(file))
    }
  })

  test('INV-12 complete files still load', async () => {
    respondJson({ schema_version: '0.3', candidates: [] })
    await expect(loadZoneFile('z', 'scenarios.json')).resolves.toBeTruthy()
    respondJson({ schema_version: '0.3', nodes: [], edges: [], hospitals: [], communities: [] })
    await expect(loadZoneFile('z', 'graph.json')).resolves.toBeTruthy()
    respondJson({ schema_version: '0.3', anything: 1 })
    await expect(loadZoneFile('z', 'meta.json')).resolves.toBeTruthy()
  })

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

  test('INV-06 a non-finite criticality still yields a drawable color', () => {
    const range = { min: 0, max: 10 }
    for (const value of [Number.NaN, Infinity, -Infinity]) expect(colorForCriticality(value, range)).toMatch(valid)
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
