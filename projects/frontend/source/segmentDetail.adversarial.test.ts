import { describe, expect, test } from 'bun:test'
import { detailView, parseRain, type DetailGraph, type DetailUnit } from './segmentDetail.ts'

const graph: DetailGraph = {
  edges: [],
  hospitals: [{ id: 'h1', name: 'Hospital Uno' }],
  communities: [{ id: 'c1', name: 'Ana' }, { id: 'c2', name: 'Beto' }],
}
const unit = (over: Partial<DetailUnit> = {}): DetailUnit => ({
  id: 'T-01', rank: 1, length_m: 100, edge_ids: [], criticality: 1, extra_time_s: 600, population_dependent: 10,
  affected_community_ids: ['c1'], per_community: [{ community_id: 'c1', time_s: 900, extra_s: 300, hospital_id: 'h1' }],
  alternates: [], exposure: { rain_mm_12d: 1 }, ...over,
})

describe('segment-detail adversarial', () => {
  test('a community with a route is never reported as having no route', () => {
    const view = detailView(unit({ per_community: [{ community_id: 'c1', time_s: 900, extra_s: null, hospital_id: 'h1' }] }), graph, [])
    expect(view.communities[0]!.withClosure).not.toBe('no route to the referral hospital')
  })

  test('a missing baseline entry reads "no data", not "no route"', () => {
    expect(detailView(unit(), graph, []).communities[0]!.withoutClosure).toBe('no data')
  })

  test('an unknown hospital id reads "no data"', () => {
    const view = detailView(unit({ per_community: [{ community_id: 'c1', time_s: 900, extra_s: 300, hospital_id: 'h9' }] }), graph, [])
    expect(view.communities[0]!.hospital).toBe('no data')
  })

  test('a community missing from graph.json falls back to its id', () => {
    expect(detailView(unit({ affected_community_ids: ['c7'] }), graph, []).communities[0]!.name).toBe('c7')
  })

  test('a zero extra time reads as short, not as no route', () => {
    expect(detailView(unit({ extra_time_s: 0 }), graph, []).extraTime).toBe('< 5 min')
  })

  test('rain.csv with a BOM, CRLF and a trailing blank line still parses', () => {
    expect(parseRain('﻿date,precip_mm\r\n2026-06-28,1\r\n\r\n')).toHaveLength(1)
  })

  test('rain.csv rejects negative rainfall', () => {
    expect(() => parseRain('date,precip_mm\n2026-06-28,-1\n')).toThrow('rain.csv')
  })
})
