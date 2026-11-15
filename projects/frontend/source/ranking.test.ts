import { beforeEach, describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { useAppStore } from './store.ts'
import { countWithoutImpact, listedUnits, noPopulationNote, rowView, type RankedUnit } from './ranking.ts'

const examples = new URL('../../contract/examples/mock-validated/', import.meta.url)
const read = <T>(name: string): T => JSON.parse(readFileSync(new URL(name, examples), 'utf-8')) as T
const scenarios = read<{ candidates: RankedUnit[] }>('scenarios.json')
const graph = read<{ edges: { id: string; road?: string | null }[] }>('graph.json')

const unit = (over: Partial<RankedUnit> & { id: string }): RankedUnit => ({
  rank: 1,
  length_m: 500,
  edge_ids: [],
  criticality: 0,
  extra_time_s: 600,
  population_dependent: 100,
  affected_community_ids: ['c1'],
  ...over,
})

describe('segment-ranking', () => {
  beforeEach(() => useAppStore.setState({ selectedUnitId: null }))

  test('INV-01 lists only units with an affected community, by ascending rank', () => {
    const units = [
      unit({ id: 'T-03', rank: 3 }),
      unit({ id: 'T-09', rank: 2, affected_community_ids: [] }),
      unit({ id: 'T-01', rank: 1 }),
    ]
    expect(listedUnits(units).map((u) => u.id)).toEqual(['T-01', 'T-03'])
    expect(listedUnits(scenarios.candidates).map((u) => u.rank)).toEqual([1, 2, 3, 4])
    expect(listedUnits([])).toEqual([])
  })

  test('INV-02 counts the units with no affected community', () => {
    const units = [unit({ id: 'T-01' }), unit({ id: 'T-02', affected_community_ids: [] }), unit({ id: 'T-03', affected_community_ids: [] })]
    expect(countWithoutImpact(units)).toBe(2)
    expect(countWithoutImpact(scenarios.candidates)).toBe(0)
  })

  test('INV-03 a null extra time reads as no route, never as a time', () => {
    const row = rowView(unit({ id: 'T-03', extra_time_s: null }), [], 10)
    expect(row.extraTime).toBe('sin ruta al hospital de referencia')
  })

  test('INV-03 a null population reads "sin dato", never 0', () => {
    const row = rowView(unit({ id: 'T-04', population_dependent: null }), [], 10)
    expect(row.population).toBe('sin dato')
    expect(row.population).not.toContain('0')
  })

  test('INV-03 a known population has thousands separators and the "estimada" label', () => {
    expect(rowView(unit({ id: 'T-02', population_dependent: 2300 }), [], 10).population).toBe('2 300 estimada')
    expect(rowView(unit({ id: 'T-02', population_dependent: 0 }), [], 10).population).toBe('0 estimada')
  })

  test('row label uses the most frequent road, or "Vía sin nombre"', () => {
    const edges = [
      { id: 'e1', road: 'Ruta 32' },
      { id: 'e2', road: 'Calle X' },
      { id: 'e3', road: 'Calle X' },
      { id: 'e4', road: null },
    ]
    expect(rowView(unit({ id: 'T-05', edge_ids: ['e1', 'e2', 'e3'] }), edges, 10).label).toBe('Calle X · T-05')
    expect(rowView(unit({ id: 'T-06', edge_ids: ['e4', 'e99'] }), edges, 10).label).toBe('Vía sin nombre · T-06')
    expect(rowView(unit({ id: 'T-01', edge_ids: ['e1'] }), graph.edges, 10).label).toBe('Ruta 32 · T-01')
  })

  test('row length is in metres below 1 000 and in km with a decimal comma otherwise', () => {
    const length = (m: number) => rowView(unit({ id: 'T-01', length_m: m }), [], 10).length
    expect(length(850)).toBe('850 m')
    expect(length(999.6)).toBe('1,0 km')
    expect(length(8700)).toBe('8,7 km')
    expect(length(12400)).toBe('12,4 km')
  })

  test('INV-05 the bar is proportional to the zone maximum and hidden when it is 0', () => {
    expect(rowView(unit({ id: 'T-02', criticality: 50 }), [], 200).barFraction).toBe(0.25)
    expect(rowView(unit({ id: 'T-02', criticality: 0 }), [], 0).barFraction).toBeNull()
    expect(noPopulationNote(scenarios.candidates)).toBe(false)
    const noPeople = scenarios.candidates.map((u) => ({ ...u, criticality: 0 }))
    expect(noPopulationNote(noPeople)).toBe(true)
  })

  test('INV-07 selecting a unit puts it in the store', () => {
    useAppStore.getState().selectUnit('T-02')
    expect(useAppStore.getState().selectedUnitId).toBe('T-02')
    useAppStore.getState().selectUnit('T-01')
    expect(useAppStore.getState().selectedUnitId).toBe('T-01')
  })
})
