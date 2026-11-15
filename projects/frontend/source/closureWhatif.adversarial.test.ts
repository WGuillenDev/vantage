import { afterEach, describe, expect, test } from 'bun:test'
import { simulate, simulationView } from './closureWhatif.ts'
import { computeAccess, type CommunityAccess, type GraphData } from './graph.ts'
import type { CorridorGraph } from './mapCorridor.ts'
import type { BaselineEntry, DetailUnit } from './segmentDetail.ts'
import { loadZoneFile } from './storage.ts'

// Attacks by /breaker closure-whatif: boundaries the claims leave open and mutation survivors.

const realFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = realFetch
})
const respondJson = (body: unknown) => {
  globalThis.fetch = (async () => ({ ok: true, status: 200, json: async () => body })) as unknown as typeof fetch
}

// Same slow reference as graph.test.ts (one Bellman-Ford per community, hospital by time then number).
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
    for (let pass = 0; pass < g.nodes.length + 1; pass++) {
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

function rng(seed: number): () => number {
  let state = seed
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296
    return state / 4294967296
  }
}

describe('computeAccess adversarial', () => {
  test('INV-04 zero-time edges and hospitals sharing nodes still pick the lowest hospital number', () => {
    const random = rng(11)
    for (let round = 0; round < 400; round++) {
      const pick = (n: number) => Math.floor(random() * n)
      const size = 8
      const g: GraphData = {
        nodes: Array.from({ length: size }, (_, i) => ({ id: `n${i + 1}`, lon: i, lat: 0 })),
        edges: Array.from({ length: 16 }, (_, i) => ({
          id: `e${i + 1}`,
          from: `n${pick(size) + 1}`,
          to: `n${pick(size) + 1}`,
          time_s: pick(4), // 0 to 3: many zero-cost edges and ties
          oneway: random() < 0.4,
        })),
        hospitals: [9, 2, 10, 1].map((n) => ({ id: `h${n}`, node: `n${pick(size) + 1}` })), // nodes may repeat
        communities: Array.from({ length: 6 }, (_, i) => ({ id: `c${i + 1}`, node: `n${pick(size) + 1}` })),
      }
      const closed = new Set(g.edges.filter(() => random() < 0.3).map((e) => e.id))
      expect(computeAccess(g, [...closed])).toEqual(reference(g, closed))
    }
  })

  test('INV-04 two hospitals on the same node: the lower number wins whatever the list order', () => {
    const g: GraphData = {
      nodes: [{ id: 'a', lon: 0, lat: 0 }],
      edges: [],
      hospitals: [
        { id: 'h10', node: 'a' },
        { id: 'h3', node: 'a' },
      ],
      communities: [{ id: 'c1', node: 'a' }],
    }
    expect(computeAccess(g, [])).toEqual([{ community_id: 'c1', time_s: 0, hospital_id: 'h3' }])
  })

  test('INV-04 a hospital reached through a zero-cost edge beats a higher-numbered hospital on the community node', () => {
    const g: GraphData = {
      nodes: ['x', 'y'].map((id, i) => ({ id, lon: i, lat: 0 })),
      edges: [{ id: 'e1', from: 'x', to: 'y', time_s: 0 }],
      hospitals: [
        { id: 'h10', node: 'x' },
        { id: 'h2', node: 'y' },
      ],
      communities: [{ id: 'c1', node: 'x' }],
    }
    expect(computeAccess(g, [])[0]).toEqual({ community_id: 'c1', time_s: 0, hospital_id: 'h2' })
  })

  test('closing edges the graph does not have, or the same edge twice, changes nothing', () => {
    const g: GraphData = {
      nodes: ['a', 'b'].map((id, i) => ({ id, lon: i, lat: 0 })),
      edges: [{ id: 'e1', from: 'a', to: 'b', time_s: 5 }],
      hospitals: [{ id: 'h1', node: 'b' }],
      communities: [{ id: 'c1', node: 'a' }],
    }
    expect(computeAccess(g, ['e99', 'e99'])).toEqual(computeAccess(g, []))
    expect(computeAccess(g, ['e1', 'e1'])[0]).toEqual({ community_id: 'c1', time_s: null, hospital_id: null })
  })

  test('a community on a node that no edge reaches has no route, and a graph with no hospitals gives none to anyone', () => {
    const g: GraphData = {
      nodes: ['a', 'b'].map((id, i) => ({ id, lon: i, lat: 0 })),
      edges: [{ id: 'e1', from: 'a', to: 'b', time_s: 5 }],
      hospitals: [{ id: 'h1', node: 'b' }],
      communities: [
        { id: 'c1', node: 'ghost' },
        { id: 'c2', node: 'a' },
      ],
    }
    expect(computeAccess(g, [])[0]).toEqual({ community_id: 'c1', time_s: null, hospital_id: null })
    expect(computeAccess({ ...g, hospitals: [] }, []).every((row) => row.time_s === null)).toBe(true)
  })
})

// h1 at a; c10 (listed first) at b and c2 at c; closing T-01 cuts both from the hospital.
const small = (): { graph: CorridorGraph; units: DetailUnit[]; baseline: BaselineEntry[] } => ({
  graph: {
    nodes: ['a', 'b', 'c'].map((id, i) => ({ id, lon: i, lat: 0 })),
    edges: [
      { id: 'e1', from: 'a', to: 'b', time_s: 10, road: 'Ruta 1', candidate_id: 'T-01', geometry: [[0, 0], [1, 0]] },
      { id: 'e2', from: 'a', to: 'c', time_s: 10, road: 'Ruta 1', candidate_id: 'T-01', geometry: [[0, 0], [2, 0]] },
    ],
    hospitals: [{ id: 'h1', name: 'Hospital 1', node: 'a' }],
    communities: [
      { id: 'c10', name: 'Diez', node: 'b', population: 10 },
      { id: 'c2', name: 'Dos', node: 'c', population: 2 },
      { id: 'c3', name: 'En el hospital', node: 'a', population: 3 },
    ],
  },
  units: [
    { id: 'T-01', rank: 1, length_m: 1, edge_ids: ['e1', 'e2'], criticality: 1, extra_time_s: null, population_dependent: 12, affected_community_ids: ['c10', 'c2'] },
  ],
  baseline: [
    { community_id: 'c10', time_s: 10, hospital_id: 'h1' },
    { community_id: 'c2', time_s: 10, hospital_id: 'h1' },
    { community_id: 'c3', time_s: 0, hospital_id: 'h1' },
  ],
})

describe('simulate adversarial', () => {
  test('INV-06 communities without a route are ordered by community number, not by text', () => {
    const { graph, units, baseline } = small()
    expect(simulate(graph, units, baseline, ['T-01']).rows.map((row) => row.communityId)).toEqual(['c2', 'c10'])
  })

  test('INV-06 a community that already sits on a hospital (time 0) is never affected', () => {
    const { graph, units, baseline } = small()
    expect(simulate(graph, units, baseline, ['T-01']).rows.map((row) => row.communityId)).not.toContain('c3')
  })

  test('INV-08 all affected communities without a route: no extra time, both counted, population summed', () => {
    const { graph, units, baseline } = small()
    expect(simulate(graph, units, baseline, ['T-01'])).toMatchObject({ extraTime_s: null, withoutRoute: 2, population: 12 })
  })

  test('INV-09 a closed id the zone does not list gives no chip and no failure', () => {
    const { graph, units, baseline } = small()
    const view = simulationView(graph, units, baseline, ['T-99', 'T-01'])
    expect(view.chips.map((chip) => chip.id)).toEqual(['T-01'])
    expect(simulationView(graph, units, baseline, ['T-99']).chips).toEqual([])
  })

  test('INV-12 a unit with no alternates field closes without highlighting anything', () => {
    const { graph, units, baseline } = small()
    expect(simulationView(graph, units, baseline, ['T-01']).alternateEdgeIds).toEqual([])
  })
})

describe('graph.json boundaries of the simulation', () => {
  const graph = (edges: unknown[]) => ({
    schema_version: '0.3',
    nodes: [{ id: 'a', lon: 0, lat: 0 }],
    edges,
    hospitals: [{ id: 'h1', name: 'H', node: 'a' }],
    communities: [{ id: 'c1', name: 'C', node: 'a', population: 5 }],
  })

  test('an edge with time_s 0 is valid (the contract minimum is 0)', async () => {
    respondJson(graph([{ id: 'e1', from: 'a', to: 'a', time_s: 0, candidate_id: null }]))
    await expect(loadZoneFile('z', 'graph.json')).resolves.toBeDefined()
  })
})
