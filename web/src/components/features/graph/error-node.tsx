import { Handle, Position } from '@xyflow/react'

export function ErrorNode({ data }: { data: Record<string, string> }) {
  return (
    <div className="bg-red-500 text-white rounded-lg px-3 py-2 shadow-md min-w-[140px] text-xs">
      <Handle type="target" position={Position.Left} className="!bg-red-300" />
      <div className="font-mono font-bold text-red-100 text-[10px] mb-0.5">error</div>
      <div className="font-semibold line-clamp-2">{data.label}</div>
      {data.detail && <div className="text-red-200 mt-0.5">{data.detail}</div>}
      <Handle type="source" position={Position.Right} className="!bg-red-300" />
    </div>
  )
}
