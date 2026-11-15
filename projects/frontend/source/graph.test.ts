import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { computeAccess, type CommunityAccess, type GraphData } from './graph.ts'

const examples = new URL('../../contract/examples/mock-validated/', import.meta.url)
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
  test('INV-01 matches the baseline with no closed edges', () => {
    expect(computeAccess(graph, [])).toEqual(scenarios.baseline)
  })

  for (const candidate of scenarios.candidates) {
    test(`INV-02 matches per_community when ${candidate.id} is closed`, () => {
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

  test('INV-02 reports c4 as isolated when T-03 is closed', () => {
    const t03 = scenarios.candidates.find((candidate) => candidate.id === 'T-03')!
    const c4 = byCommunity(computeAccess(graph, t03.edge_ids)).get('c4')
    expect(c4).toEqual({ community_id: 'c4', time_s: null, hospital_id: null })
  })

  test('INV-03 respects oneway edges', () => {
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

// A community between two hospitals, both 10 s away: h10 listed first, so list order and hospital number disagree.
const tie = (hospitals: GraphData['hospitals']): GraphData => ({
  nodes: ['a', 'b', 'c'].map((id, i) => ({ id, lon: i, lat: 0 })),
  edges: [
    { id: 'e1', from: 'a', to: 'b', time_s: 10 },
    { id: 'e2', from: 'a', to: 'c', time_s: 10 },
  ],
  hospitals,
  communities: [{ id: 'c1', node: 'a' }],
})

describe('computeAccess ties', () => {
  test('INV-04 reports the hospital with the lowest number, not the first listed', () => {
    const access = computeAccess(
      tie([
        { id: 'h10', node: 'b' },
        { id: 'h2', node: 'c' },
      ]),
      [],
    )
    expect(access).toEqual([{ community_id: 'c1', time_s: 10, hospital_id: 'h2' }])
  })

  test('INV-04 compares hospital numbers, not ids as text', () => {
    const access = computeAccess(
      tie([
        { id: 'h2', node: 'b' },
        { id: 'h10', node: 'c' },
      ]),
      [],
    )
    expect(access[0]?.hospital_id).toBe('h2')
  })

  test('INV-04 a nearer hospital still wins over a lower number', () => {
    const g = tie([
      { id: 'h1', node: 'b' },
      { id: 'h9', node: 'c' },
    ])
    g.edges[0]!.time_s = 30
    expect(computeAccess(g, [])[0]).toEqual({ community_id: 'c1', time_s: 10, hospital_id: 'h9' })
  })
})

// Reference: one Bellman-Ford per community, hospital chosen by (time, number). Slow, but it shares nothing with computeAccess.
function reference(g: GraphData, closed: Set<string>): CommunityAccess[] {
  const arcs: [string, string, number][] = []
  for (const e of g.edges) {
    if (closed.has(e.id)) continue
    arcs.push([e.from, e.to, e.time_s])
    if (e.oneway !== true) arcs.push([e.to, e.from, e.time_s])
  }
  const number = (id: string) => Number(id.replace(/\D/g, ''))
  return g.communities.map((community) => {
    const best = new Map<string, number>([[community.node, 0]])
    for (let pass = 0; pass < g.nodes.length; pass++) {
      for (const [from, to, time] of arcs) {
        const known = best.get(from)
        if (known !== undefined && known + time < (best.get(to) ?? Infinity)) best.set(to, known + time)
      }
    }
    let pick: { time: number; id: string } | null = null
    for (const h of g.hospitals) {
      const time = best.get(h.node)
      if (time === undefined) continue
      if (!pick || time < pick.time || (time === pick.time && number(h.id) < number(pick.id))) pick = { time, id: h.id }
    }
    return { community_id: community.id, time_s: pick?.time ?? null, hospital_id: pick?.id ?? null }
  })
}

// Small deterministic generator, so a failure reproduces.
function rng(seed: number): () => number {
  let state = seed
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296
    return state / 4294967296
  }
}

function randomGraph(random: () => number): GraphData {
  const size = 12
  const pick = (n: number) => Math.floor(random() * n)
  const nodes = Array.from({ length: size }, (_, i) => ({ id: `n${i + 1}`, lon: i, lat: 0 }))
  const edges = Array.from({ length: 26 }, (_, i) => ({
    id: `e${i + 1}`,
    from: `n${pick(size) + 1}`,
    to: `n${pick(size) + 1}`,
    time_s: 1 + pick(6), // small range on purpose: many equal times, so many ties
    oneway: random() < 0.5,
  }))
  const numbers = [3, 12, 7, 25]
  const hospitals = Array.from({ length: 3 }, (_, i) => ({ id: `h${numbers[i]}`, node: `n${pick(size) + 1}` }))
  const communities = Array.from({ length: 5 }, (_, i) => ({ id: `c${i + 1}`, node: `n${pick(size) + 1}` }))
  return { nodes, edges, hospitals, communities }
}

describe('computeAccess against a slow reference', () => {
  test('INV-01 INV-02 INV-03 INV-04 agree on random graphs with random closures', () => {
    const random = rng(7)
    for (let round = 0; round < 300; round++) {
      const g = randomGraph(random)
      const closed = new Set(g.edges.filter(() => random() < 0.25).map((e) => e.id))
      expect(computeAccess(g, [...closed])).toEqual(reference(g, closed))
    }
  })
})

describe('computeAccess size', () => {
  // Not INV-15 (that is a manual claim on the real graph): a sense check that the cost does not grow with communities.
  test('a graph of the Ruta 32 size answers in well under a second', () => {
    const side = 84
    const nodes = Array.from({ length: side * side }, (_, i) => ({ id: `n${i + 1}`, lon: i % side, lat: Math.floor(i / side) }))
    const edges: GraphData['edges'] = []
    for (let i = 0; i < side * side; i++) {
      if (i % side < side - 1) edges.push({ id: `e${edges.length + 1}`, from: `n${i + 1}`, to: `n${i + 2}`, time_s: 30 + (i % 7), oneway: i % 3 === 0 })
      if (i + side < side * side) edges.push({ id: `e${edges.length + 1}`, from: `n${i + 1}`, to: `n${i + side + 1}`, time_s: 40 + (i % 5) })
    }
    const g: GraphData = {
      nodes,
      edges,
      hospitals: [1, 3000, 7000].map((n, i) => ({ id: `h${i + 1}`, node: `n${n}` })),
      communities: Array.from({ length: 758 }, (_, i) => ({ id: `c${i + 1}`, node: `n${1 + ((i * 9) % nodes.length)}` })),
    }
    const start = performance.now()
    const access = computeAccess(g, ['e10', 'e11', 'e500'])
    expect(performance.now() - start).toBeLessThan(1000)
    expect(access).toHaveLength(758)
  })
})
