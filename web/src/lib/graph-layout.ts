import type { GraphNode, GraphEdge } from '@/types'

const TIER_X: Record<string, number> = {
  commit: 0,
  error: 240,
  trace: 480,
  message: 720,
  generation: 0,
  span: 0,
  event: 0,
}

const TIER_Y_STEP = 130

/**
 * Assign positions to nodes based on their type.
 *
 * horizontal: commit (x=0) → error (x=240) → trace (x=480) → message (x=720)
 *   Used for incident graphs.
 *
 * vertical: nodes laid out top-to-bottom following edge order.
 *   Used for single-trace graphs where parent-child depth matters.
 */
export function autoLayout(
  nodes: GraphNode[],
  edges: GraphEdge[],
  direction: 'horizontal' | 'vertical' = 'horizontal',
): GraphNode[] {
  if (!nodes.length) return nodes

  if (direction === 'horizontal') {
    const yCounters: Record<string, number> = {}
    return nodes.map((node) => {
      const type = node.type ?? 'event'
      const x = TIER_X[type] ?? 600
      const y = (yCounters[type] ?? 0) * TIER_Y_STEP
      yCounters[type] = (yCounters[type] ?? 0) + 1
      return { ...node, position: { x, y } }
    })
  }

  // vertical: topological sort via edge map, then assign depth
  const childrenMap = new Map<string, string[]>()
  const parentCount = new Map<string, number>()
  nodes.forEach((n) => { childrenMap.set(n.id, []); parentCount.set(n.id, 0) })
  edges.forEach((e) => {
    childrenMap.get(e.source)?.push(e.target)
    parentCount.set(e.target, (parentCount.get(e.target) ?? 0) + 1)
  })

  const depthMap = new Map<string, number>()
  const queue = nodes.filter((n) => (parentCount.get(n.id) ?? 0) === 0).map((n) => n.id)
  queue.forEach((id) => depthMap.set(id, 0))

  while (queue.length) {
    const cur = queue.shift()!
    const depth = depthMap.get(cur) ?? 0
    for (const child of childrenMap.get(cur) ?? []) {
      const prev = depthMap.get(child) ?? 0
      depthMap.set(child, Math.max(prev, depth + 1))
      queue.push(child)
    }
  }

  const xAtDepth: Record<number, number> = {}
  return nodes.map((node) => {
    const depth = depthMap.get(node.id) ?? 0
    const x = (xAtDepth[depth] ?? 0) * 200
    xAtDepth[depth] = (xAtDepth[depth] ?? 0) + 1
    return { ...node, position: { x, y: depth * TIER_Y_STEP } }
  })
}
