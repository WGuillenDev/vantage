import { describe, expect, test } from 'bun:test'
import { resolveActiveZone } from './zones.ts'
import type { Area } from './storage.ts'

const zone = (id: string, validated: boolean): Area => ({ id, name: id, bbox: [0, 0, 1, 1], validated })
const list = [zone('a', false), zone('b', true), zone('c', true)]

// Same rule as `map-corridor` (Active zone): store, then ?area, then first validated, then first.
describe('resolveActiveZone', () => {
  test('prefers a listed store id, then a listed ?area id', () => {
    expect(resolveActiveZone(list, 'c', 'a')?.id).toBe('c')
    expect(resolveActiveZone(list, null, 'a')?.id).toBe('a')
  })

  test('ignores ids that are not listed and falls back to the first validated, then the first', () => {
    expect(resolveActiveZone(list, 'zz', 'yy')?.id).toBe('b')
    expect(resolveActiveZone([zone('a', false)], null, null)?.id).toBe('a')
    expect(resolveActiveZone([], null, null)).toBeUndefined()
  })
})
