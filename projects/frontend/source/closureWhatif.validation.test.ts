import { afterEach, describe, expect, test } from 'bun:test'
import { loadZoneFile } from './storage.ts'

// The simulation reads from, to, time_s and oneway of every edge and the population of every community,
// so graph.json is refused at load, naming the file, when they are wrong (closure-whatif, trust boundary).
const realFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = realFetch
})
const respondJson = (body: unknown) => {
  globalThis.fetch = (async () => ({ ok: true, status: 200, json: async () => body })) as unknown as typeof fetch
}

const edge = { id: 'e1', from: 'a', to: 'b', time_s: 10, oneway: false, candidate_id: null }
const graph = (over: Record<string, unknown> = {}) => ({
  schema_version: '0.3',
  nodes: [{ id: 'a', lon: -84, lat: 10 }],
  edges: [edge],
  hospitals: [{ id: 'h1', name: 'Hospital', node: 'a' }],
  communities: [{ id: 'c1', name: 'Comunidad', node: 'a', population: 100 }],
  ...over,
})

describe('graph.json fields the simulation reads', () => {
  test('a graph with a valid edge and community loads, with oneway or population absent or null', async () => {
    respondJson(graph())
    await expect(loadZoneFile('z', 'graph.json')).resolves.toBeDefined()
    const { oneway: _oneway, ...twoWay } = edge
    respondJson(graph({ edges: [twoWay], communities: [{ id: 'c1', name: 'C', node: 'a', population: null }] }))
    await expect(loadZoneFile('z', 'graph.json')).resolves.toBeDefined()
    respondJson(graph({ communities: [{ id: 'c1', name: 'C', node: 'a' }] }))
    await expect(loadZoneFile('z', 'graph.json')).resolves.toBeDefined()
  })

  test.each([
    ['an edge without time_s', { ...edge, time_s: undefined }],
    ['an edge with a text time_s', { ...edge, time_s: '10' }],
    ['an edge with a negative time_s', { ...edge, time_s: -1 }],
    ['an edge with an infinite time_s', { ...edge, time_s: Infinity }],
    ['an edge without from', { ...edge, from: undefined }],
    ['an edge with a numeric to', { ...edge, to: 2 }],
    ['an edge with a text oneway', { ...edge, oneway: 'yes' }],
  ])('graph.json with %s is rejected naming the file', async (_name, bad) => {
    respondJson(graph({ edges: [bad] }))
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })

  test.each([
    ['a text population', 'many'],
    ['a negative population', -5],
    ['a fractional population', 1.5],
  ])('graph.json with a community with %s is rejected naming the file', async (_name, population) => {
    respondJson(graph({ communities: [{ id: 'c1', name: 'C', node: 'a', population }] }))
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })
})
