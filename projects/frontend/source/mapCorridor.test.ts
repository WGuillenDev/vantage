import { afterEach, beforeEach, describe, expect, test } from 'bun:test'
import { readdirSync, readFileSync } from 'node:fs'
import { loadAreas, loadZoneFile, type Area } from './storage.ts'
import { useAppStore } from './store.ts'
import { resolveActiveZone } from './zones.ts'
import {
  checkSchemaVersion,
  colorForCriticality,
  fitBounds,
  GRAY,
  legendRange,
  pointFeatures,
  rankingUnknown,
  unitFeatures,
  type CorridorGraph,
} from './mapCorridor.ts'
import type { RankedUnit } from './ranking.ts'

const zone = (id: string, validated: boolean): Area => ({ id, name: id, bbox: [0, 0, 1, 1], validated })

const unit = (id: string, criticality: number, affected: string[]): RankedUnit => ({
  id,
  rank: 1,
  length_m: 100,
  edge_ids: [],
  criticality,
  extra_time_s: null,
  population_dependent: null,
  affected_community_ids: affected,
})

const graph: CorridorGraph = {
  schema_version: '0.3',
  nodes: [
    { id: 'n1', lon: -83.9, lat: 10.1 },
    { id: 'n2', lon: -83.8, lat: 10.2 },
    { id: 'n3', lon: -83.7, lat: 10.3 },
  ],
  edges: [
    { id: 'e1', from: 'n1', to: 'n2', time_s: 1, candidate_id: 'T-01', geometry: [[-83.9, 10.1], [-83.8, 10.2]] },
    { id: 'e2', from: 'n2', to: 'n1', time_s: 1, candidate_id: 'T-01', geometry: [[-83.8, 10.2], [-83.9, 10.1]] },
    { id: 'e3', from: 'n2', to: 'n3', time_s: 1, candidate_id: null, geometry: [[-83.8, 10.2], [-83.7, 10.3]] },
    { id: 'e4', from: 'n1', to: 'n3', time_s: 1, candidate_id: 'T-99', geometry: [[-83.9, 10.1], [-83.7, 10.3]] },
    { id: 'e5', from: 'n3', to: 'n1', time_s: 1, candidate_id: 'T-02', geometry: [[-83.7, 10.3], [-83.9, 10.1]] },
  ],
  hospitals: [{ id: 'h1', name: 'Hospital A', node: 'n3' }],
  communities: [
    { id: 'c1', name: 'Comunidad 1', node: 'n1' },
    { id: 'c2', name: 'Comunidad 2', node: 'n2' },
  ],
}

const luminance = (hex: string): number => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  return 0.2126 * (r ?? 0) + 0.7152 * (g ?? 0) + 0.0722 * (b ?? 0)
}

describe('map-corridor: pure rules', () => {
  test('INV-01 an ?area id listed in areas.json is the active zone', () => {
    const list = [zone('a', true), zone('b', false)]
    expect(resolveActiveZone(list, null, 'b')?.id).toBe('b')
  })

  test('INV-02 without a valid ?area the first validated zone wins, else the first', () => {
    expect(resolveActiveZone([zone('a', false), zone('b', true)], null, 'nope')?.id).toBe('b')
    expect(resolveActiveZone([zone('a', false), zone('b', false)], null, null)?.id).toBe('a')
  })

  test('INV-04 every edge of a scenarios unit is drawn in that unit, both carriageways', () => {
    const units = [unit('T-01', 5, ['c1']), unit('T-02', 1, [])]
    const features = unitFeatures(graph, units).features
    const t01 = features.find((feature) => feature.properties.id === 'T-01')
    expect(t01?.geometry.coordinates).toHaveLength(2)
    expect(features.find((feature) => feature.properties.id === 'T-02')?.geometry.coordinates).toHaveLength(1)
    // null candidate_id and ids unknown to scenarios.json are not drawn
    expect(features.map((feature) => feature.properties.id).sort()).toEqual(['T-01', 'T-02'])
  })

  test('INV-06 a unit without affected communities is gray', () => {
    const features = unitFeatures(graph, [unit('T-01', 0, []), unit('T-02', 9, ['c1'])]).features
    expect(features.find((feature) => feature.properties.id === 'T-01')?.properties.color).toBe(GRAY)
    expect(features.find((feature) => feature.properties.id === 'T-02')?.properties.color).not.toBe(GRAY)
  })

  test('INV-06 the color is monotone in criticality', () => {
    const range = { min: 0, max: 100 }
    const lums = [0, 10, 25, 50, 75, 100].map((value) => luminance(colorForCriticality(value, range)))
    for (let i = 1; i < lums.length; i++) expect(lums[i]!).toBeLessThanOrEqual(lums[i - 1]!)
    expect(lums[0]!).toBeGreaterThan(lums[lums.length - 1]!)
  })

  test('INV-06 a zone with equal criticalities does not divide by zero', () => {
    expect(colorForCriticality(0, { min: 0, max: 0 })).toMatch(/^#[0-9a-f]{6}$/)
  })

  test('INV-07 the legend range is the lowest and highest criticality among units with an affected community', () => {
    const units = [unit('T-01', 3, ['c1']), unit('T-02', 8, ['c1']), unit('T-03', 0, [])]
    expect(legendRange(units)).toEqual({ min: 3, max: 8 })
    expect(legendRange([unit('T-03', 5, [])])).toEqual({ min: 0, max: 0 })
    expect(legendRange([])).toEqual({ min: 0, max: 0 })
  })

  test('INV-07 the colors use the legend range: the lowest affected unit is the ramp start, the highest its end', () => {
    const units = [unit('T-01', 3, ['c1']), unit('T-02', 8, ['c1']), unit('T-03', 0, [])]
    const g: CorridorGraph = {
      ...graph,
      edges: ['T-01', 'T-02', 'T-03'].map((id) => ({
        id: `e-${id}`, from: 'n1', to: 'n2', time_s: 1, candidate_id: id, geometry: [[-83.9, 10.1], [-83.8, 10.2]],
      })),
    }
    const color = (id: string) => unitFeatures(g, units).features.find((f) => f.properties.id === id)!.properties.color
    expect(color('T-01')).toBe('#fde725')
    expect(color('T-02')).toBe('#440154')
    expect(color('T-03')).toBe(GRAY)
  })

  test('INV-16 the ranking is unknown when every unit with an affected community has criticality 0', () => {
    expect(rankingUnknown([unit('T-01', 0, ['c1']), unit('T-02', 0, ['c2']), unit('T-03', 0, [])])).toBe(true)
    expect(rankingUnknown([unit('T-01', 0, ['c1']), unit('T-02', 2, ['c2'])])).toBe(false)
    expect(rankingUnknown([unit('T-03', 0, [])])).toBe(false)
    expect(rankingUnknown([])).toBe(false)
  })

  test('INV-16 a unit with an unknown criticality is not mistaken for 0', () => {
    expect(rankingUnknown([unit('T-01', Number.NaN, ['c1'])])).toBe(false)
  })

  test('INV-08 hospitals and communities are exactly those of graph.json, at their nodes', () => {
    const { hospitals, communities } = pointFeatures(graph)
    expect(hospitals.features.map((f) => f.geometry.coordinates)).toEqual([[-83.7, 10.3]])
    expect(communities.features.map((f) => f.properties.id)).toEqual(['c1', 'c2'])
    expect(communities.features.map((f) => f.geometry.coordinates)).toEqual([[-83.9, 10.1], [-83.8, 10.2]])
  })

  test('INV-14 the map fits the zone bbox', () => {
    expect(fitBounds([-84.2, 9.95, -83.7, 10.3])).toEqual([[-84.2, 9.95], [-83.7, 10.3]])
  })
})

describe('map-corridor: INV-12 data errors', () => {
  const realFetch = globalThis.fetch
  afterEach(() => {
    globalThis.fetch = realFetch
  })
  const respond = (body: unknown, ok = true, status = 200) => {
    globalThis.fetch = (async () => ({ ok, status, json: async () => body })) as unknown as typeof fetch
  }

  test('INV-12 a wrong schema_version names the file in Spanish', () => {
    expect(() => checkSchemaVersion('graph.json', { schema_version: '0.2' })).toThrow(/graph\.json/)
    expect(() => checkSchemaVersion('graph.json', {})).toThrow(/graph\.json/)
    expect(() => checkSchemaVersion('graph.json', { schema_version: '0.3' })).not.toThrow()
  })

  test('INV-12 a failed request names the file', async () => {
    respond(null, false, 404)
    await expect(loadZoneFile('z', 'scenarios.json')).rejects.toThrow(/scenarios\.json/)
    await expect(loadAreas()).rejects.toThrow(/areas\.json/)
  })

  test('INV-12 a loaded file with the wrong version is rejected', async () => {
    respond({ schema_version: '0.1' })
    await expect(loadZoneFile('z', 'meta.json')).rejects.toThrow(/meta\.json/)
    await expect(loadAreas()).rejects.toThrow(/areas\.json/)
  })

  test('INV-12 a network failure also names the file', async () => {
    globalThis.fetch = (async () => {
      throw new TypeError('offline')
    }) as unknown as typeof fetch
    await expect(loadZoneFile('z', 'graph.json')).rejects.toThrow(/graph\.json/)
  })
})

describe('map-corridor: store', () => {
  beforeEach(() => useAppStore.setState({ activeZoneId: 'a', selectedUnitId: null }))

  test('INV-11 changing the active zone clears the selected unit', () => {
    useAppStore.getState().selectUnit('T-01')
    useAppStore.getState().setActiveZone('b')
    expect(useAppStore.getState().activeZoneId).toBe('b')
    expect(useAppStore.getState().selectedUnitId).toBeNull()
  })

  test('INV-09 selecting and clearing a unit goes through the store', () => {
    useAppStore.getState().selectUnit('T-02')
    expect(useAppStore.getState().selectedUnitId).toBe('T-02')
    useAppStore.getState().selectUnit(null)
    expect(useAppStore.getState().selectedUnitId).toBeNull()
  })
})

describe('map-corridor: INV-15 forbidden words', () => {
  const dir = new URL('./', import.meta.url)
  const sources = readdirSync(dir)
    .filter((name) => /\.tsx?$/.test(name) && !name.endsWith('.test.ts'))
    .map((name) => ({ name, text: readFileSync(new URL(name, dir), 'utf-8') }))

  test('INV-15 no source contains the forbidden words', () => {
    const allowed = /no son derrumbes confirmados|no es un derrumbe confirmado/gi
    for (const { name, text } of sources) {
      const lower = text.toLowerCase()
      expect({ name, hit: /candidato|causado por|funciona en cualquier lugar/.test(lower) }).toEqual({ name, hit: false })
      expect({ name, hit: /confirmad/.test(lower.replace(allowed, '')) }).toEqual({ name, hit: false })
    }
  })
})
