import { beforeEach, describe, expect, test } from 'bun:test'
import { useAppStore } from './store.ts'
import { chooseZone, zoneOptions } from './zones.ts'
import type { Area } from './storage.ts'

const fakeHistory = () => {
  const urls: string[] = []
  return { urls, replaceState: (_state: unknown, _title: string, url: string | URL | null | undefined) => urls.push(String(url)) }
}

describe('zone-picker adversarial (INV-04)', () => {
  beforeEach(() => useAppStore.setState({ activeZoneId: null }))

  test('INV-04 an id with reserved characters round-trips through the query string', () => {
    const history = fakeHistory()
    const id = 'río & co=1#x?y'
    chooseZone(id, history, 'https://x.test/vantage/')
    expect(new URL(history.urls[0] ?? '').searchParams.get('area')).toBe(id)
    expect(new URL(history.urls[0] ?? '').hash).toBe('')
  })

  test('INV-04 repeated area parameters collapse to one carrying the chosen id', () => {
    const history = fakeHistory()
    chooseZone('b', history, 'https://x.test/?area=a&area=c')
    expect(new URL(history.urls[0] ?? '').searchParams.getAll('area')).toEqual(['b'])
  })

  test('INV-04 choosing twice leaves the last zone in the store and one replace per choice', () => {
    const history = fakeHistory()
    chooseZone('a', history, 'https://x.test/?area=z')
    chooseZone('b', history, history.urls[0] ?? '')
    expect(useAppStore.getState().activeZoneId).toBe('b')
    expect(history.urls).toHaveLength(2)
    expect(new URL(history.urls[1] ?? '').searchParams.getAll('area')).toEqual(['b'])
  })

  test('INV-01 an empty list gives no options and the input is not reordered or mutated', () => {
    expect(zoneOptions([])).toEqual([])
    const list: Area[] = [
      { id: 'z', name: 'Z', bbox: [0, 0, 1, 1], validated: true },
      { id: 'a', name: 'A', bbox: [0, 0, 1, 1], validated: false },
    ]
    const copy = structuredClone(list)
    zoneOptions(list)
    expect(list).toEqual(copy)
  })
})
