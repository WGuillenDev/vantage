import { describe, expect, test } from 'bun:test'
import { formatDuration } from './format.ts'

// Rule owned by `trust-signals` (INV-07, INV-08); first used by `segment-ranking`.
describe('formatDuration', () => {
  test('INV-07 under 300 seconds reads "< 5 min"', () => {
    expect(formatDuration(0)).toBe('< 5 min')
    expect(formatDuration(299)).toBe('< 5 min')
  })

  test('INV-08 rounds half up to a multiple of 5 minutes under an hour', () => {
    expect(formatDuration(300)).toBe('≈ 5 min')
    expect(formatDuration(1140)).toBe('≈ 20 min') // 19 min
    expect(formatDuration(12.5 * 60)).toBe('≈ 15 min') // half rounds up
    expect(formatDuration(12.4 * 60)).toBe('≈ 10 min')
  })

  test('INV-08 from 60 minutes it is written in hours, after rounding', () => {
    expect(formatDuration(57.5 * 60)).toBe('≈ 1 h') // rounds to 60
    expect(formatDuration(60 * 60)).toBe('≈ 1 h')
    expect(formatDuration(75 * 60)).toBe('≈ 1 h 15 min')
    expect(formatDuration(125 * 60)).toBe('≈ 2 h 5 min')
  })
})
