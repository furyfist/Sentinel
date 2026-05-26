export { CommitNode } from './commit-node'
export { ErrorNode } from './error-node'
export { TraceNode } from './trace-node'
export { MessageNode } from './message-node'
export { GenerationNode } from './generation-node'
export { SpanNode } from './span-node'

export const NODE_TYPES = {
  commit: CommitNode,
  error: ErrorNode,
  trace: TraceNode,
  message: MessageNode,
  generation: GenerationNode,
  span: SpanNode,
  event: SpanNode,
} as const
