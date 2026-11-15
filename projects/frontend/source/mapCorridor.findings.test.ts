import { afterEach, describe, expect, test } from 'bun:test'
import { loadZoneFile } from './storage.ts'

// Defects found by /breaker map-corridor (round 2), now pinned as INV-17 and INV-18.
const realFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = realFetch
})
const respondJson = (body: unknown) => {
  globalThis.fetch = (async () => ({ ok: true, status: 200, json: async () => body })) as unknown as typeof fetch
}

const edge = { id: 'e1', from: 'a', to: 'b', time_s: 1, candidate_id: 'T-01', geometry: [[-84, 10], [-83.9, 10.1]] }
const graph = (over: Record<string, unknown> = {}) => ({
  schema_version: '0.3',
  nodes: [{ id: 'a', lon: -84, lat: 10 }],
  edges: [edge],
  hospitals: [{ id: 'h1', name: 'Hospital', node: 'a' }],
  communities: [{ id: 'c1', name: 'Comunidad', node: 'a' }],
  ...over,
})
const unit = { id: 'T-01', criticality: 1, affected_community_ids: [] }

describe('map-corridor INV-17: malformed elements inside the required lists', () => {
  test('INV-17 a well-formed graph.json and scenarios.json load', async () => {
    respondJson(graph({ edges: [edge, { ...edge, id: 'e2', candidate_id: null, geometry: undefined }] }))
    await expect(loadZoneFile('z', 'graph.json')).resolves.toBeDefined()
    respondJson({ schema_version: '0.3', candidates: [unit] })
    await expect(loadZoneFile('z', 'scenarios.json')).resolves.toBeDefined()
  })

  test('INV-17 graph.json with a null edge is rejected naming the file', async () => {
    respondJson(graph({ edges: [null] }))
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })

  test('INV-17 graph.json with a unit edge without geometry is rejected naming the file', async () => {
    const { geometry: _geometry, ...bare } = edge
    respondJson(graph({ edges: [bare] }))
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })

  test.each([
    ['one position', [[-84, 10]]],
    ['a non-numeric position', [[-84, 10], ['x', 1]]],
    ['a position of one number', [[-84, 10], [1]]],
    ['a geometry that is not a list', 'LINESTRING'],
  ])('INV-17 graph.json with a unit edge geometry of %s is rejected', async (_name, geometry) => {
    respondJson(graph({ edges: [{ ...edge, geometry }] }))
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })

  test.each([
    ['an edge without id', { ...edge, id: undefined }],
    ['an edge with a numeric candidate_id', { ...edge, candidate_id: 7 }],
    ['an edge without candidate_id', { ...edge, candidate_id: undefined }],
  ])('INV-17 graph.json with %s is rejected', async (_name, bad) => {
    respondJson(graph({ edges: [bad] }))
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })

  test.each([
    ['hospitals', { name: 'H', node: 'a' }],
    ['hospitals', { id: 'h1', node: 'a' }],
    ['hospitals', { id: 'h1', name: 'H' }],
    ['communities', null],
    ['communities', { id: 'c1', name: 'C' }],
  ])('INV-17 graph.json with a malformed element of %s is rejected', async (list, bad) => {
    respondJson(graph({ [list]: [bad] }))
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })

  test('INV-17 scenarios.json with a unit without affected_community_ids is rejected naming the file', async () => {
    respondJson({ schema_version: '0.3', candidates: [{ id: 'T-01', criticality: 1 }] })
    await expect(loadZoneFile('z', 'scenarios.json')).rejects.toThrow(/scenarios\.json/)
  })

  test.each([
    ['a null unit', null],
    ['a unit without id', { criticality: 1, affected_community_ids: [] }],
    ['a unit with a string criticality', { ...unit, criticality: '3' }],
    ['a unit with a NaN criticality', { ...unit, criticality: Number.NaN }],
    ['a unit with an affected list that is not a list', { ...unit, affected_community_ids: 'c1' }],
  ])('INV-17 scenarios.json with %s is rejected', async (_name, bad) => {
    respondJson({ schema_version: '0.3', candidates: [bad] })
    await expect(loadZoneFile('z', 'scenarios.json')).rejects.toThrow(/scenarios\.json/)
  })
})

describe('map-corridor INV-18: references to nodes', () => {
  test.each([
    ['hospitals', { id: 'h1', name: 'H', node: 'missing' }],
    ['communities', { id: 'c1', name: 'C', node: 'missing' }],
  ])('INV-18 a %s node that graph.json does not list is rejected naming graph.json', async (list, bad) => {
    respondJson(graph({ [list]: [bad] }))
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })

  test('INV-18 one dangling community rejects the whole zone, not just that point', async () => {
    respondJson(graph({ communities: [{ id: 'c1', name: 'C', node: 'a' }, { id: 'c2', name: 'D', node: 'zz' }] }))
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })
})
