import { Handle, Position } from '@xyflow/react'

export function GenerationNode({ data }: { data: Record<string, unknown> }) {
  const isError = data.is_error as boolean
  return (
    <div className={`rounded-lg px-3 py-2 shadow-md min-w-[150px] text-xs border ${
      isError ? 'bg-red-50 border-red-300 text-red-800' : 'bg-violet-50 border-violet-200 text-violet-900'
    }`}>
      <Handle type="target" position={Position.Top} className={isError ? '!bg-red-400' : '!bg-violet-400'} />
      <div className={`font-mono font-bold text-[10px] mb-0.5 ${isError ? 'text-red-400' : 'text-violet-400'}`}>
        {isError ? 'error' : 'generation'}
      </div>
      <div className="font-semibold">{data.label as string}</div>
      {data.model && <div className="text-[10px] opacity-60 mt-0.5">{data.model as string}</div>}
      <div className="flex gap-2 mt-1 text-[10px] opacity-70">
        {(data.cost as number) > 0 && <span>${(data.cost as number).toFixed(4)}</span>}
        {(data.tokens as number) > 0 && <span>{data.tokens as number}t</span>}
      </div>
      <Handle type="source" position={Position.Bottom} className={isError ? '!bg-red-400' : '!bg-violet-400'} />
    </div>
  )
}
