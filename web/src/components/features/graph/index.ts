import { CommitNode } from './commit-node'
import { ErrorNode } from './error-node'
import { TraceNode } from './trace-node'
import { MessageNode } from './message-node'
import { GenerationNode } from './generation-node'
import { SpanNode } from './span-node'

export { CommitNode, ErrorNode, TraceNode, MessageNode, GenerationNode, SpanNode }

export const NODE_TYPES = {
  commit: CommitNode,
  error: ErrorNode,
  trace: TraceNode,
  message: MessageNode,
  generation: GenerationNode,
  span: SpanNode,
  event: SpanNode,
} as const
