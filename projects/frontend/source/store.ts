import { create } from 'zustand'

// Minimal store for `zone-picker`; `map-corridor` owns it and extends it (selected unit, closed set).
interface AppState {
  activeZoneId: string | null
  setActiveZone: (id: string) => void
}

export const useAppStore = create<AppState>((set) => ({
  activeZoneId: null,
  setActiveZone: (id) => set({ activeZoneId: id }),
}))
