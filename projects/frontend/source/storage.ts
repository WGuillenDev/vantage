export interface Area {
  id: string
  name: string
  bbox: [number, number, number, number]
  validated: boolean
}

const STORAGE = `${import.meta.env.BASE_URL}storage/`

export async function loadAreas(): Promise<Area[]> {
  const response = await fetch(`${STORAGE}areas.json`)
  if (!response.ok) {
    throw new Error(`Could not load areas.json (${response.status}); run "make mock"`)
  }
  return ((await response.json()) as { areas: Area[] }).areas
}

// The zone picker (`zone-picker` slice) will choose the zone; until then the first one is used.
export async function loadDefaultZone(): Promise<{ area: Area; base: string }> {
  const [area] = await loadAreas()
  if (!area) throw new Error('areas.json lists no zones')
  return { area, base: `${STORAGE}${area.id}/` }
}
