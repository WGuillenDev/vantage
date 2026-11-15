import { checkSchemaVersion, fileErrorMessage } from './mapCorridor.ts'

export interface Area {
  id: string
  name: string
  bbox: [number, number, number, number]
  validated: boolean
}

const STORAGE = `${import.meta.env.BASE_URL}storage/`

// Every data file is read here: a failed request or a wrong schema_version names the file (map-corridor INV-12).
async function readJson<T>(url: string, file: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(url)
  } catch {
    throw new Error(fileErrorMessage(file, 'sin conexión o archivo inaccesible'))
  }
  if (!response.ok) throw new Error(fileErrorMessage(file, `error ${response.status}`))
  const data: unknown = await response.json()
  checkSchemaVersion(file, data)
  return data as T
}

export async function loadAreas(): Promise<Area[]> {
  return (await readJson<{ areas: Area[] }>(`${STORAGE}areas.json`, 'areas.json')).areas
}

export const loadZoneFile = <T>(zoneId: string, file: string): Promise<T> =>
  readJson<T>(`${STORAGE}${zoneId}/${file}`, file)
