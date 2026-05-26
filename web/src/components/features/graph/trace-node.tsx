import { Handle, Position } from '@xyflow/react'

export function TraceNode({ data }: { data: Record<string, string> }) {
  return (
    <div className="bg-amber-500 text-white rounded-lg px-3 py-2 shadow-md min-w-[140px] text-xs">
      <Handle type="target" position={Position.Left} className="!bg-amber-300" />
      <div className="font-mono font-bold text-amber-100 text-[10px] mb-0.5">trace</div>
      <div className="font-semibold">{data.label}</div>
      {data.detail && <div className="text-amber-100 mt-0.5">{data.detail}</div>}
      {data.trace_id && (
        <div className="font-mono text-amber-200 text-[10px] mt-1">{(data.trace_id as string).slice(0, 12)}…</div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-amber-300" />
    </div>
  )
}
