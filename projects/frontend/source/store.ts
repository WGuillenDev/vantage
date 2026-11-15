import { create } from 'zustand'

// Minimal store: `zone-picker` (active zone) and `segment-ranking` (selected unit).
// `map-corridor` owns it and extends it (closed set, etc.).
interface AppState {
  activeZoneId: string | null
  setActiveZone: (id: string) => void
  selectedUnitId: string | null
  selectUnit: (id: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  activeZoneId: null,
  setActiveZone: (id) => set({ activeZoneId: id }),
  selectedUnitId: null,
  selectUnit: (id) => set({ selectedUnitId: id }),
}))
