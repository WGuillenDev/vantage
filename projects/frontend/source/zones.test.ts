import { beforeEach, describe, expect, test } from 'bun:test'
import { readFileSync } from 'node:fs'
import { useAppStore } from './store.ts'
import { chooseZone, showsZoneControl, zoneOptions } from './zones.ts'
import type { Area } from './storage.ts'

const examples = new URL('../../contract/examples/', import.meta.url)
const areas = (JSON.parse(readFileSync(new URL('areas.json', examples), 'utf-8')) as { areas: Area[] }).areas

const zone = (id: string, validated: boolean): Area => ({ id, name: `Zone ${id}`, bbox: [0, 0, 1, 1], validated })

describe('zone-picker', () => {
  beforeEach(() => useAppStore.setState({ activeZoneId: null }))

  test('INV-01 lists every zone in file order', () => {
    const list = [zone('b', true), zone('a', true), zone('c', true)]
    expect(zoneOptions(list).map((option) => option.id)).toEqual(['b', 'a', 'c'])
    expect(zoneOptions(areas).map((option) => option.id)).toEqual(areas.map((area) => area.id))
  })

  test('INV-02 labels only the zones that are not validated', () => {
    const options = zoneOptions([zone('a', true), zone('b', false)])
    expect(options[0]?.label).toBe('Zone a')
    expect(options[1]?.label).toBe('Zone b (no validada)')
  })

  test('INV-03 shows the control only with two or more zones', () => {
    expect(showsZoneControl([zone('a', true)])).toBe(false)
    expect(showsZoneControl([zone('a', true), zone('b', true)])).toBe(true)
    expect(showsZoneControl([])).toBe(false)
  })

  test('INV-04 sets the store and replaces the URL without a history entry', () => {
    const calls: { method: string; url: string }[] = []
    const history = {
      replaceState: (_state: unknown, _title: string, url: string) => calls.push({ method: 'replace', url }),
      pushState: (_state: unknown, _title: string, url: string) => calls.push({ method: 'push', url }),
    }
    chooseZone('b', history, 'https://x.test/vantage/?area=a&lang=es#top')
    expect(useAppStore.getState().activeZoneId).toBe('b')
    expect(calls).toHaveLength(1)
    expect(calls[0]?.method).toBe('replace')
    const url = new URL(calls[0]?.url ?? '')
    expect(url.searchParams.get('area')).toBe('b')
    expect(url.searchParams.get('lang')).toBe('es')
    expect(url.hash).toBe('#top')
  })
})
