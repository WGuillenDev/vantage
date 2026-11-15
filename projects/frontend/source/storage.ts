import { checkSchemaVersion, fileErrorMessage } from './mapCorridor.ts'

export interface Area {
  id: string
  name: string
  bbox: [number, number, number, number]
  validated: boolean
}

const STORAGE = `${import.meta.env.BASE_URL}storage/`

// Lists each file must carry; a file without them would crash the UI later instead of failing here.
const REQUIRED_LISTS: Record<string, string[]> = {
  'areas.json': ['areas'],
  'graph.json': ['nodes', 'edges', 'hospitals', 'communities'],
  'scenarios.json': ['candidates'],
}

// Every data file is read here: a failed request, bad JSON, a wrong schema_version or a missing list names the file (map-corridor INV-12).
async function readJson<T>(url: string, file: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(url)
  } catch {
    throw new Error(fileErrorMessage(file, 'sin conexión o archivo inaccesible'))
  }
  if (!response.ok) throw new Error(fileErrorMessage(file, `error ${response.status}`))
  let data: unknown
  try {
    data = await response.json()
  } catch {
    throw new Error(fileErrorMessage(file, 'el contenido no es JSON válido'))
  }
  checkSchemaVersion(file, data)
  for (const key of REQUIRED_LISTS[file] ?? []) {
    if (!Array.isArray((data as Record<string, unknown>)[key])) {
      throw new Error(fileErrorMessage(file, `falta la lista "${key}"`))
    }
  }
  return data as T
}

export async function loadAreas(): Promise<Area[]> {
  return (await readJson<{ areas: Area[] }>(`${STORAGE}areas.json`, 'areas.json')).areas
}

export const loadZoneFile = <T>(zoneId: string, file: string): Promise<T> =>
  readJson<T>(`${STORAGE}${zoneId}/${file}`, file)
