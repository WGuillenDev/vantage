import { describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { REFERRAL_NOTE, attributionLines, isUnvalidated, readingPanel, simulationNote, suspectLabel } from './trustSignals.ts'
import type { Area } from './storage.ts'

const examples = new URL('../../contract/examples/', import.meta.url)
const read = <T>(path: string): T => JSON.parse(readFileSync(new URL(path, examples), 'utf-8')) as T
const meta = read<Parameters<typeof readingPanel>[0]>('mock-validated/meta.json')
const graph = read<Parameters<typeof readingPanel>[1]>('mock-validated/graph.json')
const areas = read<{ areas: Area[] }>('areas.json').areas

describe('trust-signals', () => {
  test('INV-02 the footer lists every attribution string of the zone', () => {
    expect(attributionLines(meta)).toEqual(meta.attributions)
    expect(attributionLines({ ...meta, attributions: [] })).toEqual([])
  })

  test('INV-03 the banner shows only for a zone with validated false', () => {
    expect(isUnvalidated(areas.find((a) => !a.validated))).toBe(true)
    expect(isUnvalidated(areas.find((a) => a.validated))).toBe(false)
    expect(isUnvalidated(undefined)).toBe(false)
  })

  test('INV-04 the reading panel carries speeds, referral hospitals and the radar note', () => {
    const panel = readingPanel(meta, graph)
    expect(panel.speeds).toEqual([
      { roadClass: 'primary', kmh: 60 },
      { roadClass: 'secondary', kmh: 40 },
      { roadClass: 'tertiary', kmh: 30 },
    ])
    expect(panel.hospitals).toEqual(graph.hospitals.map((h) => h.name))
    expect(panel.radarNote).toBe(meta.detection_limits?.note ?? null)
    expect(panel.radarNote).not.toBeNull()
  })

  test('INV-04 the radar note is absent when the zone has no detection_limits', () => {
    const { detection_limits: _removed, ...rest } = meta
    expect(readingPanel(rest, graph).radarNote).toBeNull()
  })

  test('INV-05 only a suspect isolated community gets the model-artifact mark', () => {
    const base = 'sin ruta al hospital de referencia'
    expect(suspectLabel('c4', ['c4'])).toBe(`${base} (posible artefacto del modelo)`)
    expect(suspectLabel('c2', ['c4'])).toBe(base)
    expect(suspectLabel('c2', [])).toBe(base)
  })

  test('INV-06 the simulation note shows while at least one community has no route', () => {
    expect(simulationNote(1)).toBe('Las comunidades sin ruta pueden incluir artefactos del modelo.')
    expect(simulationNote(3)).toBe('Las comunidades sin ruta pueden incluir artefactos del modelo.')
    expect(simulationNote(0)).toBeNull()
  })
})

describe('referral-set note', () => {
  test('says the order depends on the referral hospitals and never claims a cause', () => {
    expect(REFERRAL_NOTE).toContain('hospitales cuentan como referencia')
    expect(REFERRAL_NOTE).not.toMatch(/confirmad|causa/i)
  })
})
