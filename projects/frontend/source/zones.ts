import type { Area } from './storage.ts'
import { useAppStore } from './store.ts'

export const zoneOptions = (areas: Area[]): { id: string; label: string }[] =>
  areas.map((area) => ({ id: area.id, label: area.validated ? area.name : `${area.name} (no validada)` }))

export const showsZoneControl = (areas: Area[]): boolean => areas.length >= 2

// Replaces the URL entry (no history push), so a shared link still opens the chosen zone.
export function chooseZone(
  id: string,
  history: Pick<History, 'replaceState'> = window.history,
  href: string = window.location.href,
): void {
  const url = new URL(href)
  url.searchParams.set('area', id)
  useAppStore.getState().setActiveZone(id)
  history.replaceState(null, '', url)
}
