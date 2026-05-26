import { Handle, Position } from '@xyflow/react'

export function MessageNode({ data }: { data: Record<string, string> }) {
  return (
    <div className="bg-teal-500 text-white rounded-lg px-3 py-2 shadow-md min-w-[140px] text-xs">
      <Handle type="target" position={Position.Left} className="!bg-teal-300" />
      <div className="font-mono font-bold text-teal-100 text-[10px] mb-0.5">slack</div>
      <div className="font-semibold">{data.label}</div>
      {data.detail && <div className="text-teal-100 mt-0.5 line-clamp-2">{data.detail}</div>}
      <Handle type="source" position={Position.Right} className="!bg-teal-300" />
    </div>
  )
}
