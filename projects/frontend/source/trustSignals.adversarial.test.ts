import { describe, expect, test } from 'bun:test'
import { formatDuration, formatPopulation } from './format.ts'
import { NOTICE, UNVALIDATED_BANNER, isUnvalidated, readingPanel, suspectLabel } from './trustSignals.ts'

// Independent oracle: integer arithmetic, no division by 60.
const oracle = (seconds: number): string => {
  if (seconds < 300) return '< 5 min'
  const minutes = Math.floor((seconds + 150) / 300) * 5
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  if (h === 0) return `≈ ${m} min`
  return m === 0 ? `≈ ${h} h` : `≈ ${h} h ${m} min`
}

describe('trust-signals adversarial', () => {
  test('INV-07 INV-08 formatDuration agrees with an integer oracle on every second up to 5.5 h', () => {
    for (let s = 0; s <= 20000; s++) expect(formatDuration(s)).toBe(oracle(s))
  })

  test('INV-08 durations are monotonic and half-minute inputs do not drift', () => {
    let last = 0
    for (let s = 0; s <= 20000; s += 0.5) {
      const text = formatDuration(s)
      const minutes = text.startsWith('<') ? 0 : Number(/(\d+) h/.exec(text)?.[1] ?? 0) * 60 + Number(/(\d+) min/.exec(text)?.[1] ?? 0)
      expect(minutes).toBeGreaterThanOrEqual(last)
      last = minutes
    }
  })

  test('INV-01 INV-03 the notice and banner texts are exactly the spec wording', () => {
    expect(NOTICE).toBe('Critical segments by consequence; not confirmed landslides.')
    expect(UNVALIDATED_BANNER).toBe('Unvalidated zone: its results have not been reviewed.')
    expect(NOTICE.replace('not confirmed landslides', '')).not.toMatch(/confirm/i)
  })

  test('INV-03 a zone with validated true never gets the banner', () => {
    expect(isUnvalidated({ id: 'a', name: 'A', bbox: [0, 0, 1, 1], validated: true })).toBe(false)
  })

  test('INV-04 empty speeds and hospitals give empty lists, a null detection_limits gives no note', () => {
    const panel = readingPanel({ speed_model_kmh: {}, attributions: [], detection_limits: null as never }, { hospitals: [] })
    expect(panel).toEqual({ speeds: [], hospitals: [], radarNote: null })
  })

  test('INV-04 hospital names keep their file order', () => {
    const panel = readingPanel({ speed_model_kmh: {}, attributions: [] }, { hospitals: [{ name: 'Z' }, { name: 'A' }] })
    expect(panel.hospitals).toEqual(['Z', 'A'])
  })

  test('INV-05 the mark matches the whole community id, not a prefix or substring', () => {
    expect(suspectLabel('c1', ['c10'])).toBe('no route to the referral hospital')
    expect(suspectLabel('c10', ['c1'])).toBe('no route to the referral hospital')
  })

  test('INV-09 separators hold at 1 000 and 100 000 and the label is always last', () => {
    expect(formatPopulation(1000)).toBe('1,000 estimated')
    expect(formatPopulation(100000)).toBe('100,000 estimated')
    expect(formatPopulation(12)).toBe('12 estimated')
  })
})
