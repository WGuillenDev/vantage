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

type Json = Record<string, unknown>
const isObject = (value: unknown): value is Json => typeof value === 'object' && value !== null && !Array.isArray(value)
const isText = (value: unknown): value is string => typeof value === 'string' && value !== ''
const isPosition = (value: unknown): boolean =>
  Array.isArray(value) && value.length >= 2 && value.slice(0, 2).every((n) => typeof n === 'number' && Number.isFinite(n))

// Returns what is wrong with the first malformed element of a required list, or null (INV-17, INV-18).
function elementProblem(file: string, data: Json): string | null {
  if (file === 'scenarios.json') {
    const bad = (data.candidates as unknown[]).findIndex(
      (unit) =>
        !isObject(unit) ||
        !isText(unit.id) ||
        typeof unit.criticality !== 'number' ||
        !Number.isFinite(unit.criticality) ||
        !Array.isArray(unit.affected_community_ids),
    )
    return bad >= 0 ? `el tramo ${bad + 1} de "candidates" está mal formado` : null
  }
  if (file !== 'graph.json') return null
  const badEdge = (data.edges as unknown[]).findIndex(
    (edge) =>
      !isObject(edge) ||
      !isText(edge.id) ||
      // closure-whatif routes on these: a missing time would become NaN without a message.
      !isText(edge.from) ||
      !isText(edge.to) ||
      typeof edge.time_s !== 'number' ||
      !(Number.isFinite(edge.time_s) && edge.time_s >= 0) ||
      !(edge.oneway === undefined || typeof edge.oneway === 'boolean') ||
      !(edge.candidate_id === null || isText(edge.candidate_id)) ||
      (edge.candidate_id !== null && !(Array.isArray(edge.geometry) && edge.geometry.length >= 2 && edge.geometry.every(isPosition))),
  )
  if (badEdge >= 0) return `la arista ${badEdge + 1} de "edges" está mal formada`
  const nodes = new Set((data.nodes as unknown[]).map((node) => (isObject(node) ? node.id : undefined)))
  for (const list of ['hospitals', 'communities']) {
    for (const [index, item] of (data[list] as unknown[]).entries()) {
      if (!isObject(item) || !isText(item.id) || !isText(item.name) || !isText(item.node)) {
        return `el elemento ${index + 1} de "${list}" está mal formado`
      }
      if (!nodes.has(item.node)) return `"${list}" usa el nodo "${item.node}", que no está en "nodes"`
      const { population } = item
      if (list === 'communities' && !(population === undefined || population === null || (Number.isInteger(population) && (population as number) >= 0))) {
        return `la comunidad ${index + 1} de "communities" tiene una población no válida`
      }
    }
  }
  return null
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
  const problem = elementProblem(file, data as Json)
  if (problem) throw new Error(fileErrorMessage(file, problem))
  return data as T
}

export const rainUrl = (zoneId: string): string => `${STORAGE}${zoneId}/rain.csv`

export async function loadAreas(): Promise<Area[]> {
  return (await readJson<{ areas: Area[] }>(`${STORAGE}areas.json`, 'areas.json')).areas
}

export const loadZoneFile = <T>(zoneId: string, file: string): Promise<T> =>
  readJson<T>(`${STORAGE}${zoneId}/${file}`, file)
