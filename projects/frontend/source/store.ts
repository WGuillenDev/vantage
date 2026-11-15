import { create } from 'zustand'

// Minimal store: `zone-picker` (active zone) and `segment-ranking` (selected unit).
// `map-corridor` owns it and extends it (closed set, etc.).
interface AppState {
  activeZoneId: string | null
  setActiveZone: (id: string) => void
  selectedUnitId: string | null
  selectUnit: (id: string | null) => void
  // The unit under the pointer in the list, highlighted on the map.
  hoveredUnitId: string | null
  hoverUnit: (id: string | null) => void
  // The closed set of the simulation (`closure-whatif`); `segment-detail` adds to it.
  closedUnitIds: string[]
  closeUnit: (id: string) => void
  openUnit: (id: string) => void
  resetClosed: () => void
}

export const useAppStore = create<AppState>((set) => ({
  activeZoneId: null,
  setActiveZone: (id) => set({ activeZoneId: id, selectedUnitId: null, closedUnitIds: [] }),
  selectedUnitId: null,
  selectUnit: (id) => set({ selectedUnitId: id }),
  hoveredUnitId: null,
  hoverUnit: (id) => set({ hoveredUnitId: id }),
  closedUnitIds: [],
  closeUnit: (id) => set((state) => (state.closedUnitIds.includes(id) ? state : { closedUnitIds: [...state.closedUnitIds, id] })),
  openUnit: (id) => set((state) => ({ closedUnitIds: state.closedUnitIds.filter((closed) => closed !== id) })),
  resetClosed: () => set({ closedUnitIds: [] }),
}))
