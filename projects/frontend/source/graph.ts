export interface GraphData {
  nodes: { id: string; lon: number; lat: number }[]
  edges: { id: string; from: string; to: string; time_s: number; oneway?: boolean }[]
  hospitals: { id: string; node: string }[]
  communities: { id: string; node: string }[]
}

export interface CommunityAccess {
  community_id: string
  time_s: number | null
  hospital_id: string | null
}

type Arc = { from: string; time_s: number }
// time, hospital number, node, hospital id: the heap orders by time and then by hospital number.
type HeapItem = [time_s: number, number: number, node: string, hospital_id: string]

export async function loadGraph(zoneBase: string): Promise<GraphData> {
  const response = await fetch(`${zoneBase}graph.json`)
  if (!response.ok) {
    throw new Error(`Could not load graph.json (${response.status}); run "make mock"`)
  }
  return (await response.json()) as GraphData
}

// Routes run community -> hospital, so the search walks the edges backwards from the hospitals.
function buildReverseAdjacency(graph: GraphData, closed: ReadonlySet<string>): Map<string, Arc[]> {
  const reverse = new Map<string, Arc[]>()
  const add = (to: string, from: string, time_s: number) => {
    const arcs = reverse.get(to)
    if (arcs) arcs.push({ from, time_s })
    else reverse.set(to, [{ from, time_s }])
  }
  for (const edge of graph.edges) {
    if (closed.has(edge.id)) continue
    add(edge.to, edge.from, edge.time_s)
    if (edge.oneway !== true) add(edge.from, edge.to, edge.time_s)
  }
  return reverse
}

const before = (a: HeapItem, b: HeapItem): boolean => a[0] < b[0] || (a[0] === b[0] && a[1] < b[1])

function pushHeap(heap: HeapItem[], item: HeapItem): void {
  heap.push(item)
  let i = heap.length - 1
  while (i > 0) {
    const parent = (i - 1) >> 1
    if (!before(heap[i]!, heap[parent]!)) break
    ;[heap[parent], heap[i]] = [heap[i]!, heap[parent]!]
    i = parent
  }
}

function popHeap(heap: HeapItem[]): HeapItem {
  const top = heap[0]!
  const last = heap.pop()!
  if (heap.length > 0) {
    heap[0] = last
    let i = 0
    for (;;) {
      const left = 2 * i + 1
      const right = left + 1
      let smallest = i
      if (left < heap.length && before(heap[left]!, heap[smallest]!)) smallest = left
      if (right < heap.length && before(heap[right]!, heap[smallest]!)) smallest = right
      if (smallest === i) break
      ;[heap[smallest], heap[i]] = [heap[i]!, heap[smallest]!]
      i = smallest
    }
  }
  return top
}

// Hospital ids look like "h10": compare their numbers, so h2 comes before h10.
const idNumber = (id: string): number => Number(id.replace(/\D/g, ''))

// One search from every hospital at once: each node settles with its nearest hospital, ties to the lowest number.
export function computeAccess(graph: GraphData, closedEdgeIds: readonly string[]): CommunityAccess[] {
  const reverse = buildReverseAdjacency(graph, new Set(closedEdgeIds))
  const heap: HeapItem[] = []
  for (const hospital of graph.hospitals) pushHeap(heap, [0, idNumber(hospital.id), hospital.node, hospital.id])
  const settled = new Map<string, { time_s: number; hospital_id: string }>()
  while (heap.length > 0) {
    const [time_s, number, node, hospital_id] = popHeap(heap)
    if (settled.has(node)) continue
    settled.set(node, { time_s, hospital_id })
    for (const arc of reverse.get(node) ?? []) {
      if (!settled.has(arc.from)) pushHeap(heap, [time_s + arc.time_s, number, arc.from, hospital_id])
    }
  }
  return graph.communities.map((community) => {
    const route = settled.get(community.node)
    return { community_id: community.id, time_s: route?.time_s ?? null, hospital_id: route?.hospital_id ?? null }
  })
}
