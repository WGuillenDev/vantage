// Approximate duration (rule of `trust-signals`): order of magnitude, never false precision.
export function formatDuration(seconds: number): string {
  if (seconds < 300) return '< 5 min'
  const minutes = Math.floor(seconds / 60 / 5 + 0.5) * 5
  if (minutes < 60) return `≈ ${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest === 0 ? `≈ ${hours} h` : `≈ ${hours} h ${rest} min`
}
