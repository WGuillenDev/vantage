import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { computeAccess, type CommunityAccess, type GraphData } from './graph.ts'

const examples = new URL('../../contract/examples/', import.meta.url)
const read = <T>(name: string): T => JSON.parse(readFileSync(new URL(name, examples), 'utf-8')) as T

interface Scenarios {
  baseline: CommunityAccess[]
  candidates: {
    id: string
    edge_ids: string[]
    per_community: { community_id: string; time_s: number | null; hospital_id: string | null }[]
  }[]
}

const graph = read<GraphData>('graph.json')
const scenarios = read<Scenarios>('scenarios.json')

const byCommunity = (rows: CommunityAccess[]) => new Map(rows.map((row) => [row.community_id, row]))

describe('computeAccess', () => {
  test('matches the baseline with no closed edges', () => {
    expect(computeAccess(graph, [])).toEqual(scenarios.baseline)
  })

  for (const candidate of scenarios.candidates) {
    test(`matches per_community when ${candidate.id} is closed`, () => {
      const access = byCommunity(computeAccess(graph, candidate.edge_ids))
      for (const expected of candidate.per_community) {
        expect(access.get(expected.community_id)).toEqual({
          community_id: expected.community_id,
          time_s: expected.time_s,
          hospital_id: expected.hospital_id,
        })
      }
    })
  }

  test('reports c4 as isolated when T-03 is closed', () => {
    const t03 = scenarios.candidates.find((candidate) => candidate.id === 'T-03')!
    const c4 = byCommunity(computeAccess(graph, t03.edge_ids)).get('c4')
    expect(c4).toEqual({ community_id: 'c4', time_s: null, hospital_id: null })
  })

  test('respects oneway edges', () => {
    const line: GraphData = {
      nodes: [
        { id: 'n1', lon: 0, lat: 0 },
        { id: 'n2', lon: 1, lat: 0 },
      ],
      edges: [{ id: 'e1', from: 'n1', to: 'n2', time_s: 10, oneway: true }],
      hospitals: [{ id: 'h1', node: 'n2' }],
      communities: [
        { id: 'c1', node: 'n1' },
        { id: 'c2', node: 'n2' },
      ],
    }
    expect(computeAccess(line, [])).toEqual([
      { community_id: 'c1', time_s: 10, hospital_id: 'h1' },
      { community_id: 'c2', time_s: 0, hospital_id: 'h1' },
    ])
    const reversed = { ...line, hospitals: [{ id: 'h1', node: 'n1' }] }
    expect(computeAccess(reversed, [])[1]).toEqual({ community_id: 'c2', time_s: null, hospital_id: null })
  })
})
