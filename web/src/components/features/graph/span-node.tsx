import { Handle, Position } from '@xyflow/react'

export function SpanNode({ data }: { data: Record<string, unknown> }) {
  const isError = data.is_error as boolean
  return (
    <div className={`rounded-lg px-3 py-2 shadow-md min-w-[140px] text-xs border ${
      isError ? 'bg-red-50 border-red-200' : 'bg-sky-50 border-sky-200 text-sky-900'
    }`}>
      <Handle type="target" position={Position.Top} className="!bg-sky-400" />
      <div className="font-mono font-bold text-[10px] text-sky-400 mb-0.5">span</div>
      <div className="font-semibold">{data.label as string}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-sky-400" />
    </div>
  )
}
