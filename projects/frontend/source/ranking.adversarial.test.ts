import { describe, expect, test } from 'bun:test'
import { formatDuration } from './format.ts'
import { countWithoutImpact, listedUnits, maxCriticality, rowView, type RankedUnit } from './ranking.ts'

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

describe('segment-ranking adversarial', () => {
  test('INV-01 INV-02 every unit is either listed or counted, never both and never neither', () => {
    const units = [
      unit({ id: 'T-01', rank: 4 }),
      unit({ id: 'T-02', rank: 1, affected_community_ids: [] }),
      unit({ id: 'T-03', rank: 2, extra_time_s: null, population_dependent: null }),
      unit({ id: 'T-04', rank: 3, affected_community_ids: [] }),
    ]
    expect(listedUnits(units).length + countWithoutImpact(units)).toBe(units.length)
  })

  test('INV-01 listing does not reorder the caller’s array', () => {
    const units = [unit({ id: 'T-02', rank: 2 }), unit({ id: 'T-01', rank: 1 })]
    listedUnits(units)
    expect(units.map((u) => u.id)).toEqual(['T-02', 'T-01'])
  })

  test('INV-05 the top unit gets a full bar and no bar exceeds the zone maximum', () => {
    const units = [unit({ id: 'T-01', criticality: 40 }), unit({ id: 'T-02', criticality: 200 })]
    const max = maxCriticality(units)
    const bars = units.map((u) => rowView(u, [], max).barFraction)
    expect(bars).toEqual([0.2, 1])
  })

  test('INV-03 a unit with no route and no population shows both marks together', () => {
    const row = rowView(unit({ id: 'T-09', extra_time_s: null, population_dependent: null }), [], 0)
    expect(row.extraTime).toBe('sin ruta al hospital de referencia')
    expect(row.population).toBe('sin dato')
    expect(row.barFraction).toBeNull()
  })

  test('label ties go to the road met first and unnamed edges never win', () => {
    const edges = [
      { id: 'e1', road: 'Calle B' },
      { id: 'e2', road: 'Calle A' },
      { id: 'e3', road: '' },
      { id: 'e4', road: '' },
    ]
    expect(rowView(unit({ id: 'T-01', edge_ids: ['e1', 'e2', 'e3', 'e4'] }), edges, 1).label).toBe('Calle B · T-01')
  })

  test('length rounds at the 1 000 m boundary without printing "1000 m"', () => {
    const length = (m: number) => rowView(unit({ id: 'T-01', length_m: m }), [], 1).length
    expect(length(999.4)).toBe('999 m')
    expect(length(999.5)).toBe('1,0 km')
    expect(length(1000)).toBe('1,0 km')
  })

  test('population separators hold for seven digits', () => {
    expect(rowView(unit({ id: 'T-01', population_dependent: 1234567 }), [], 1).population).toBe('1 234 567 estimada')
    expect(rowView(unit({ id: 'T-01', population_dependent: 999 }), [], 1).population).toBe('999 estimada')
  })

  test('duration changes exactly at its 300 s and 5-minute rounding boundaries', () => {
    expect(formatDuration(299.999)).toBe('< 5 min')
    expect(formatDuration(300)).toBe('≈ 5 min')
    expect(formatDuration(449)).toBe('≈ 5 min') // 7.48 min
    expect(formatDuration(450)).toBe('≈ 10 min') // 7.5 min rounds up
    expect(formatDuration(3450)).toBe('≈ 1 h') // 57.5 min rounds up to 60
    expect(formatDuration(3449)).toBe('≈ 55 min')
  })
})
