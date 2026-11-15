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

type Arc = { to: string; time_s: number }
type HeapItem = [time_s: number, node: string]

export async function loadGraph(zoneBase: string): Promise<GraphData> {
  const response = await fetch(`${zoneBase}graph.json`)
  if (!response.ok) {
    throw new Error(`Could not load graph.json (${response.status}); run "make mock"`)
  }
  return (await response.json()) as GraphData
}

function buildAdjacency(graph: GraphData, closed: ReadonlySet<string>): Map<string, Arc[]> {
  const adjacency = new Map<string, Arc[]>()
  const add = (from: string, to: string, time_s: number) => {
    const arcs = adjacency.get(from)
    if (arcs) arcs.push({ to, time_s })
    else adjacency.set(from, [{ to, time_s }])
  }
  for (const edge of graph.edges) {
    if (closed.has(edge.id)) continue
    add(edge.from, edge.to, edge.time_s)
    if (edge.oneway !== true) add(edge.to, edge.from, edge.time_s)
  }
  return adjacency
}

function pushHeap(heap: HeapItem[], item: HeapItem): void {
  heap.push(item)
  let i = heap.length - 1
  while (i > 0) {
    const parent = (i - 1) >> 1
    if (heap[parent][0] <= heap[i][0]) break
    ;[heap[parent], heap[i]] = [heap[i], heap[parent]]
    i = parent
  }
}

function popHeap(heap: HeapItem[]): HeapItem {
  const top = heap[0]
  const last = heap.pop()!
  if (heap.length > 0) {
    heap[0] = last
    let i = 0
    for (;;) {
      const left = 2 * i + 1
      const right = left + 1
      let smallest = i
      if (left < heap.length && heap[left][0] < heap[smallest][0]) smallest = left
      if (right < heap.length && heap[right][0] < heap[smallest][0]) smallest = right
      if (smallest === i) break
      ;[heap[smallest], heap[i]] = [heap[i], heap[smallest]]
      i = smallest
    }
  }
  return top
}

function shortestTimes(adjacency: Map<string, Arc[]>, source: string): Map<string, number> {
  const best = new Map<string, number>([[source, 0]])
  const heap: HeapItem[] = [[0, source]]
  while (heap.length > 0) {
    const [time_s, node] = popHeap(heap)
    if (time_s > (best.get(node) ?? Infinity)) continue
    for (const arc of adjacency.get(node) ?? []) {
      const next = time_s + arc.time_s
      if (next < (best.get(arc.to) ?? Infinity)) {
        best.set(arc.to, next)
        pushHeap(heap, [next, arc.to])
      }
    }
  }
  return best
}

// shortcut: one Dijkstra per community; upgrade to one search from all hospitals if graphs get large.
export function computeAccess(graph: GraphData, closedEdgeIds: readonly string[]): CommunityAccess[] {
  const adjacency = buildAdjacency(graph, new Set(closedEdgeIds))
  return graph.communities.map((community) => {
    const times = shortestTimes(adjacency, community.node)
    let time_s: number | null = null
    let hospital_id: string | null = null
    // Strict "<" keeps the first listed hospital when two are equally close.
    for (const hospital of graph.hospitals) {
      const reached = times.get(hospital.node)
      if (reached !== undefined && (time_s === null || reached < time_s)) {
        time_s = reached
        hospital_id = hospital.id
      }
    }
    return { community_id: community.id, time_s, hospital_id }
  })
}
