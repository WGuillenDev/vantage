import { create } from 'zustand'

// Minimal store: `zone-picker` (active zone) and `segment-ranking` (selected unit).
// `map-corridor` owns it and extends it (closed set, etc.).
interface AppState {
  activeZoneId: string | null
  setActiveZone: (id: string) => void
  selectedUnitId: string | null
  selectUnit: (id: string | null) => void
  // Minimal closed set so `segment-detail` can add to it; `closure-whatif` owns the simulation.
  closedUnitIds: string[]
  closeUnit: (id: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  activeZoneId: null,
  setActiveZone: (id) => set({ activeZoneId: id, selectedUnitId: null }),
  selectedUnitId: null,
  selectUnit: (id) => set({ selectedUnitId: id }),
  closedUnitIds: [],
  closeUnit: (id) => set((state) => (state.closedUnitIds.includes(id) ? state : { closedUnitIds: [...state.closedUnitIds, id] })),
}))
