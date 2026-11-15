import { beforeEach, describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { useAppStore } from './store.ts'
import {
  detailView,
  highlightedDays,
  parseRain,
  rainErrorMessage,
  type DetailGraph,
  type DetailUnit,
} from './segmentDetail.ts'

const examples = new URL('../../contract/examples/mock-validated/', import.meta.url)
const read = (name: string): string => readFileSync(new URL(name, examples), 'utf-8')
const scenarios = JSON.parse(read('scenarios.json')) as { baseline: { community_id: string; time_s: number | null; hospital_id: string | null }[]; candidates: DetailUnit[] }
const graph = JSON.parse(read('graph.json')) as DetailGraph

const graphOf = (): DetailGraph => ({
  edges: [{ id: 'e1', road: 'Ruta 32' }],
  hospitals: [{ id: 'h1', name: 'Hospital Uno' }],
  communities: [
    { id: 'c1', name: 'Ana' },
    { id: 'c2', name: 'Beto' },
    { id: 'c3', name: 'Cora' },
    { id: 'c4', name: 'Dani' },
  ],
})
const baseline = [
  { community_id: 'c1', time_s: 600, hospital_id: 'h1' },
  { community_id: 'c2', time_s: 600, hospital_id: 'h1' },
  { community_id: 'c3', time_s: 600, hospital_id: 'h1' },
  { community_id: 'c4', time_s: 600, hospital_id: 'h1' },
]
const unit = (over: Partial<DetailUnit> = {}): DetailUnit => ({
  id: 'T-01',
  rank: 1,
  length_m: 800,
  edge_ids: ['e1'],
  criticality: 10,
  extra_time_s: 1200,
  population_dependent: 2300,
  affected_community_ids: ['c1'],
  per_community: [{ community_id: 'c1', time_s: 1800, extra_s: 1200, hospital_id: 'h1' }],
  alternates: [],
  exposure: { rain_mm_12d: 85.2 },
  ...over,
})

describe('segment-detail', () => {
  test('INV-01 shows extra time and population, with the no-route and no-data texts for null', () => {
    const ok = detailView(unit(), graphOf(), baseline)
    expect(ok.header).toBe('Ruta 32 · T-01')
    expect(ok.rank).toBe(1)
    expect(ok.extraTime).toBe('≈ 20 min')
    expect(ok.population).toBe('2 300 estimada')
    const nulls = detailView(unit({ extra_time_s: null, population_dependent: null }), graphOf(), baseline)
    expect(nulls.extraTime).toBe('sin ruta al hospital de referencia')
    expect(nulls.population).toBe('sin dato')
  })

  test('INV-02 lists exactly the affected communities: isolated first, then extra time descending, then id', () => {
    const view = detailView(
      unit({
        affected_community_ids: ['c4', 'c3', 'c2', 'c1'],
        per_community: [
          { community_id: 'c1', time_s: 900, extra_s: 300, hospital_id: 'h1' },
          { community_id: 'c2', time_s: 1500, extra_s: 900, hospital_id: 'h1' },
          { community_id: 'c3', time_s: null, extra_s: null, hospital_id: null },
          { community_id: 'c4', time_s: 1500, extra_s: 900, hospital_id: 'h1' },
        ],
      }),
      graphOf(),
      baseline,
    )
    expect(view.communities.map((c) => c.id)).toEqual(['c3', 'c2', 'c4', 'c1'])
    const [isolated, second] = view.communities
    expect(isolated!.hospital).toBe('sin ruta al hospital de referencia')
    expect(isolated!.withClosure).toBe('sin ruta al hospital de referencia')
    expect(isolated!.extra).toBe('sin ruta al hospital de referencia')
    expect(second).toMatchObject({ name: 'Beto', hospital: 'Hospital Uno', withoutClosure: '≈ 10 min', withClosure: '≈ 25 min', extra: '≈ 15 min' })
    expect(JSON.stringify(view)).not.toContain('aislada')
  })

  test('INV-02 skips ids in per_community that are not affected', () => {
    const view = detailView(unit({ per_community: [
      { community_id: 'c1', time_s: 1800, extra_s: 1200, hospital_id: 'h1' },
      { community_id: 'c2', time_s: 1800, extra_s: 1200, hospital_id: 'h1' },
    ] }), graphOf(), baseline)
    expect(view.communities.map((c) => c.id)).toEqual(['c1'])
  })

  test('INV-05 shows the alternates by vehicle, or the empty text', () => {
    expect(detailView(unit(), graphOf(), baseline).alternates).toEqual(['sin alternas registradas'])
    const view = detailView(
      unit({ alternates: [{ name: 'Ruta 126', vehicles: 'light' }, { name: 'Ruta 10', vehicles: 'freight' }] }),
      graphOf(),
      baseline,
    )
    expect(view.alternates).toEqual(['Ruta 126 · livianos', 'Ruta 10 · pesados'])
  })

  test('INV-06 a null rain value reads "sin dato", never 0', () => {
    expect(detailView(unit({ exposure: { rain_mm_12d: null } }), graphOf(), baseline).rain).toBe('sin dato')
    expect(detailView(unit({ exposure: null }), graphOf(), baseline).rain).toBe('sin dato')
    expect(detailView(unit({ exposure: undefined }), graphOf(), baseline).rain).toBe('sin dato')
    expect(detailView(unit(), graphOf(), baseline).rain).toBe('85,2 mm en 12 días')
    expect(detailView(unit({ exposure: { rain_mm_12d: 0 } }), graphOf(), baseline).rain).toBe('0 mm en 12 días')
  })

  test('INV-08 the hypothesis label always travels with the Exposición block', () => {
    for (const exposure of [{ rain_mm_12d: 3 }, { rain_mm_12d: null }, null]) {
      expect(detailView(unit({ exposure }), graphOf(), baseline).rainLabel).toBe('Hipótesis, no causa confirmada')
    }
  })

  test('INV-02 works on the contract mock', () => {
    for (const candidate of scenarios.candidates) {
      const view = detailView(candidate, graph, scenarios.baseline)
      expect(view.communities.map((c) => c.id).sort()).toEqual([...candidate.affected_community_ids].sort())
    }
  })

  test('INV-11 highlights the 12 days ending at rain.end and keeps the whole period', () => {
    const rows = parseRain('date,precip_mm\n2026-06-28,1.0\n2026-06-29,0.0\n2026-07-10,2.5\n2026-07-11,4\n')
    expect(rows).toEqual([
      { date: '2026-06-28', mm: 1 },
      { date: '2026-06-29', mm: 0 },
      { date: '2026-07-10', mm: 2.5 },
      { date: '2026-07-11', mm: 4 },
    ])
    const days = highlightedDays(rows, '2026-07-11')
    expect(days.map((d) => d.highlighted)).toEqual([false, false, true, true])
    expect(highlightedDays(rows, '2026-07-10').map((d) => d.highlighted)).toEqual([false, true, true, false])
  })

  test('INV-12 a rain.csv that cannot be read yields a Spanish message naming the file', () => {
    expect(() => parseRain('')).toThrow('rain.csv')
    expect(() => parseRain('date,precip_mm\n2026-06-28,abc\n')).toThrow('rain.csv')
    expect(() => parseRain('date,precip_mm\n')).toThrow('rain.csv')
    expect(rainErrorMessage('error 404')).toBe('No se pudo cargar rain.csv: error 404.')
  })

  describe('INV-13', () => {
    beforeEach(() => useAppStore.setState({ closedUnitIds: [] }))
    test('closing a unit adds it to the closed set once', () => {
      useAppStore.getState().closeUnit('T-01')
      useAppStore.getState().closeUnit('T-01')
      useAppStore.getState().closeUnit('T-02')
      expect(useAppStore.getState().closedUnitIds).toEqual(['T-01', 'T-02'])
    })
  })
})

describe('suspect isolation mark in the detail card (trust-signals INV-05)', () => {
  const unit = {
    ...scenarios.candidates[0]!,
    affected_community_ids: ['c1', 'c2'],
    per_community: [
      { community_id: 'c1', time_s: null, extra_s: null, hospital_id: null },
      { community_id: 'c2', time_s: null, extra_s: null, hospital_id: null },
    ],
    suspect_isolated_community_ids: ['c1'],
  } as DetailUnit
  const baseline = [
    { community_id: 'c1', time_s: 600, hospital_id: 'h1' },
    { community_id: 'c2', time_s: 600, hospital_id: 'h1' },
  ]

  test('marks only the suspect isolated community', () => {
    const view = detailView(unit, graph, baseline)
    expect(view.communities.find((c) => c.id === 'c1')?.withClosure).toBe('sin ruta al hospital de referencia (posible artefacto del modelo)')
    expect(view.communities.find((c) => c.id === 'c2')?.withClosure).toBe('sin ruta al hospital de referencia')
  })
})
