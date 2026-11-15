import { describe, expect, test } from 'bun:test'
import { filterUnits, type RankedUnit } from './ranking.ts'

const unit = (id: string, over: Partial<RankedUnit & { suspect_isolated_community_ids: string[] }> = {}) => ({
  id,
  rank: 1,
  length_m: 100,
  edge_ids: ['e1'],
  criticality: 1,
  extra_time_s: 60,
  population_dependent: 10,
  affected_community_ids: ['c1'],
  ...over,
})
const edges = [{ id: 'e1', road: 'Ruta Braulio Carrillo' }]
const units = [unit('T-01'), unit('T-02', { extra_time_s: null }), unit('T-03', { suspect_isolated_community_ids: ['c1'] })]

describe('filterUnits', () => {
  test('the empty query and filter keep every unit', () => {
    expect(filterUnits(units, edges, '  ', 'all')).toHaveLength(3)
  })
  test('the text ignores case and accents and matches road and id', () => {
    expect(filterUnits(units, edges, 'braulio carrillo', 'all')).toHaveLength(3)
    expect(filterUnits(units, edges, 'T-02', 'all').map((u) => u.id)).toEqual(['T-02'])
    expect(filterUnits(units, edges, 'ruta braulió', 'all')).toHaveLength(3)
  })
  test('the filters keep the units without route or with suspect isolations', () => {
    expect(filterUnits(units, edges, '', 'no-route').map((u) => u.id)).toEqual(['T-02'])
    expect(filterUnits(units, edges, '', 'suspect').map((u) => u.id)).toEqual(['T-03'])
  })
})
