import { beforeEach, describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { formatDuration, formatPopulation } from './format.ts'
import {
  alternateEdgeIds,
  alternateFeatures,
  alternateRoads,
  closedEdgeIds,
  closedFeatures,
  simulate,
  simulationView,
} from './closureWhatif.ts'
import type { CorridorGraph } from './mapCorridor.ts'
import type { BaselineEntry, DetailUnit } from './segmentDetail.ts'
import { useAppStore } from './store.ts'
import { simulationNote } from './trustSignals.ts'

const examples = new URL('../../contract/examples/mock-validated/', import.meta.url)
const read = <T>(name: string): T => JSON.parse(readFileSync(new URL(name, examples), 'utf-8')) as T

const graph = read<CorridorGraph>('graph.json')
const scenarios = read<{ baseline: BaselineEntry[]; candidates: DetailUnit[] }>('scenarios.json')
const units = scenarios.candidates
const baseline = scenarios.baseline
const NO_ROUTE = 'sin ruta al hospital de referencia'

const run = (...ids: string[]) => simulate(graph, units, baseline, ids)
const view = (...ids: string[]) => simulationView(graph, units, baseline, ids)

describe('closedEdgeIds', () => {
  test('the closed edges are the union of the units edge_ids, without repeats', () => {
    expect(closedEdgeIds(units, ['T-01', 'T-02', 'T-01'])).toEqual(['e2', 'e3'])
  })

  test('a unit id that the zone does not list is ignored', () => {
    expect(closedEdgeIds(units, ['T-99', 'T-04'])).toEqual(['e4'])
    expect(closedEdgeIds(units, [])).toEqual([])
  })
})

describe('simulate', () => {
  test('INV-08 with nothing closed, nobody is affected', () => {
    expect(run()).toMatchObject({ rows: [], extraTime_s: null, withoutRoute: 0, population: null })
  })

  test('INV-08 closing one unit gives the figures of scenarios.json for that unit', () => {
    for (const unit of units) {
      const sim = run(unit.id)
      expect(sim.rows.map((row) => row.communityId).sort()).toEqual([...unit.affected_community_ids].sort())
      expect(sim.extraTime_s).toBe(unit.extra_time_s)
      expect(sim.population).toBe(unit.population_dependent)
      expect(sim.withoutRoute).toBe(unit.isolated_community_ids.length)
    }
  })

  test('INV-08 two units: the largest extra time, communities without a route and the known population', () => {
    expect(run('T-01', 'T-02')).toMatchObject({ extraTime_s: 1200, withoutRoute: 0, population: 2300 })
    // c4 has no route, c5 loses 900 s and has no known population.
    expect(run('T-03', 'T-04')).toMatchObject({ extraTime_s: 900, withoutRoute: 1, population: 300 })
  })

  test('INV-08 when every affected community has no route, there is no extra time', () => {
    expect(run('T-03')).toMatchObject({ extraTime_s: null, withoutRoute: 1, population: 300 })
  })

  test('INV-08 when no affected community has a known population, the population is unknown', () => {
    expect(run('T-04')).toMatchObject({ extraTime_s: 900, withoutRoute: 0, population: null })
  })

  test('INV-06 a community that loses every route is listed as affected, without a route', () => {
    const [row] = run('T-03').rows
    expect(row).toMatchObject({ communityId: 'c4', afterSeconds: null, extraSeconds: null, hospitalId: null })
  })

  test('INV-06 a community with no baseline route is never affected', () => {
    const lonely: CorridorGraph = {
      ...graph,
      nodes: [...graph.nodes, { id: 'n99', lon: 0, lat: 0 }],
      communities: [...graph.communities, { id: 'c99', name: 'Sola', node: 'n99', population: 50 }],
    }
    const withBaseline = [...baseline, { community_id: 'c99', time_s: null, hospital_id: null }]
    expect(simulate(lonely, units, withBaseline, ['T-01', 'T-02', 'T-03', 'T-04']).rows.map((row) => row.communityId)).not.toContain('c99')
    // A community missing from the baseline has no baseline route either.
    expect(simulate(lonely, units, baseline, ['T-03']).rows.map((row) => row.communityId)).not.toContain('c99')
  })

  test('INV-06 a community whose time does not grow is not affected', () => {
    expect(run('T-04').rows.map((row) => row.communityId)).toEqual(['c5'])
  })
})

describe('simulationView', () => {
  test('INV-06 shows "sin ruta al hospital de referencia" for a community without a route, and the model note', () => {
    const v = view('T-03')
    expect(v.rows).toEqual([
      { id: 'c4', name: 'Comunidad Mock 4', withoutClosure: formatDuration(1680), withClosure: NO_ROUTE, extra: NO_ROUTE, hospital: NO_ROUTE },
    ])
    expect(v.summary.note).toBe(simulationNote(1))
    expect(view('T-04').summary.note).toBeNull()
  })

  test('INV-08 formats the summary: durations are approximate and the population is an estimate or "sin dato"', () => {
    expect(view('T-01', 'T-02').summary).toMatchObject({ extraTime: formatDuration(1200), withoutRoute: 0, population: formatPopulation(2300) })
    expect(view('T-04').summary.population).toBe('sin dato')
    expect(view('T-03').summary.extraTime).toBe('ninguno')
  })

  test('INV-08 compares each affected community before and after, with the hospital it reaches by name', () => {
    expect(view('T-04').rows).toEqual([
      {
        id: 'c5',
        name: 'Comunidad Mock 5',
        withoutClosure: formatDuration(900),
        withClosure: formatDuration(1800),
        extra: formatDuration(900),
        hospital: 'Hospital Mock B',
      },
    ])
  })

  test('INV-06 lists the communities without a route first', () => {
    expect(view('T-03', 'T-04').rows.map((row) => row.id)).toEqual(['c4', 'c5'])
  })

  test('INV-09 one chip per closed unit, in the order it was closed, with its label', () => {
    expect(view('T-03', 'T-01').chips).toEqual([
      { id: 'T-03', label: 'Vía sin nombre · T-03' },
      { id: 'T-01', label: 'Ruta 32 · T-01' },
    ])
    expect(view().chips).toEqual([])
  })
})

describe('alternate roads', () => {
  test('INV-12 the alternates of the closed units, by name, without repeats', () => {
    expect(alternateRoads(units, ['T-01', 'T-02'])).toEqual(['Ruta 126', 'Ruta 10'])
    expect(alternateRoads(units, [])).toEqual([])
  })

  test('INV-12 the edges whose road is named like an alternate', () => {
    expect(alternateEdgeIds(graph.edges, ['Ruta 126', 'Ruta 10'])).toEqual(['e5', 'e8'])
    expect(alternateEdgeIds(graph.edges, [])).toEqual([])
  })

  test('INV-12 a closed unit without alternates highlights nothing', () => {
    const bare = units.map((unit) => ({ ...unit, alternates: [] }))
    expect(simulationView(graph, bare, baseline, ['T-01']).alternateEdgeIds).toEqual([])
    expect(view('T-01').alternateEdgeIds).toEqual(['e5', 'e8'])
    expect(view('T-01').closedEdgeIds).toEqual(['e2'])
  })
})

describe('what the map draws', () => {
  test('INV-12 the closed units are drawn with the geometry of both carriageways, and only they', () => {
    const closed = closedFeatures(graph, units, ['T-01', 'T-04'])
    expect(closed.features.map((feature) => feature.properties.id).sort()).toEqual(['T-01', 'T-04'])
    expect(closed.features.find((feature) => feature.properties.id === 'T-01')?.geometry.coordinates).toEqual([
      graph.edges.find((edge) => edge.id === 'e2')!.geometry,
    ])
    expect(closedFeatures(graph, units, []).features).toEqual([])
    expect(closedFeatures(graph, units, ['T-99']).features).toEqual([])
  })

  test('INV-12 each alternate edge is drawn as a line with its own geometry', () => {
    const lines = alternateFeatures(graph.edges, ['e5', 'e8'])
    expect(lines.features.map((feature) => feature.properties.id)).toEqual(['e5', 'e8'])
    expect(lines.features[0]?.geometry).toEqual({ type: 'LineString', coordinates: graph.edges.find((edge) => edge.id === 'e5')!.geometry })
    expect(alternateFeatures(graph.edges, []).features).toEqual([])
  })
})

describe('closed set in the store', () => {
  beforeEach(() => useAppStore.setState({ closedUnitIds: [], selectedUnitId: null, activeZoneId: null }))

  test('INV-09 closing adds the unit once, opening removes only that unit, reset empties the set', () => {
    const { closeUnit, openUnit, resetClosed } = useAppStore.getState()
    closeUnit('T-01')
    closeUnit('T-02')
    closeUnit('T-01')
    expect(useAppStore.getState().closedUnitIds).toEqual(['T-01', 'T-02'])
    openUnit('T-01')
    expect(useAppStore.getState().closedUnitIds).toEqual(['T-02'])
    resetClosed()
    expect(useAppStore.getState().closedUnitIds).toEqual([])
  })

  test('INV-09 opening a unit that is not closed changes nothing', () => {
    useAppStore.getState().closeUnit('T-01')
    useAppStore.getState().openUnit('T-09')
    expect(useAppStore.getState().closedUnitIds).toEqual(['T-01'])
  })

  test('INV-13 changing the active zone empties the closed set', () => {
    useAppStore.getState().closeUnit('T-01')
    useAppStore.getState().setActiveZone('other')
    expect(useAppStore.getState().closedUnitIds).toEqual([])
  })
})
