import { afterEach, describe, expect, test } from 'bun:test'
import { loadZoneFile } from './storage.ts'

// Defects found by /breaker closure-whatif, fixed in storage.ts.
// The simulation reads baseline, edge_ids and alternates of scenarios.json and population of graph.json,
// so a wrong file is refused at load instead of giving a silent wrong answer or a crash on render.
const realFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = realFetch
})
const respondJson = (body: unknown) => {
  globalThis.fetch = (async () => ({ ok: true, status: 200, json: async () => body })) as unknown as typeof fetch
}

const unit = {
  id: 'T-01',
  criticality: 1,
  affected_community_ids: ['c1'],
  edge_ids: ['e1'],
  alternates: [{ name: 'Ruta 126', vehicles: 'light' }],
}
const scenarios = (over: Record<string, unknown> = {}, unitOver: Record<string, unknown> = {}) => ({
  schema_version: '0.3',
  baseline: [{ community_id: 'c1', time_s: 10, hospital_id: 'h1' }],
  candidates: [{ ...unit, ...unitOver }],
  ...over,
})

describe('scenarios.json fields the simulation reads', () => {
  test('a well-formed scenarios.json loads', async () => {
    respondJson(scenarios())
    await expect(loadZoneFile('z', 'scenarios.json')).resolves.toBeDefined()
  })

  test('FINDING-1 a scenarios.json without baseline is rejected naming the file (today nobody is ever "affected")', async () => {
    const { baseline: _baseline, ...without } = scenarios()
    respondJson(without)
    await expect(loadZoneFile('z', 'scenarios.json')).rejects.toThrow(/scenarios\.json/)
  })

  test('FINDING-1 a baseline entry that is not an object is rejected naming the file (today it crashes the render)', async () => {
    respondJson(scenarios({ baseline: [null] }))
    await expect(loadZoneFile('z', 'scenarios.json')).rejects.toThrow(/scenarios\.json/)
  })

  test('FINDING-2 a unit without edge_ids is rejected naming the file (today closing it silently does nothing)', async () => {
    const { edge_ids: _edgeIds, ...bare } = unit
    respondJson({ ...scenarios(), candidates: [bare] })
    await expect(loadZoneFile('z', 'scenarios.json')).rejects.toThrow(/scenarios\.json/)
  })

  test('FINDING-3 a unit whose alternates is not a list is rejected naming the file (today it crashes the render)', async () => {
    respondJson(scenarios({}, { alternates: { name: 'Ruta 126' } }))
    await expect(loadZoneFile('z', 'scenarios.json')).rejects.toThrow(/scenarios\.json/)
  })
})

describe('graph.json population', () => {
  test('FINDING-4 a community with population 0 is rejected (the contract: unknown is null, never 0, minimum 1)', async () => {
    respondJson({
      schema_version: '0.3',
      nodes: [{ id: 'a', lon: 0, lat: 0 }],
      edges: [],
      hospitals: [{ id: 'h1', name: 'H', node: 'a' }],
      communities: [{ id: 'c1', name: 'C', node: 'a', population: 0 }],
    })
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })
})
