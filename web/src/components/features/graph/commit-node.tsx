import { Handle, Position } from '@xyflow/react'

export function CommitNode({ data }: { data: Record<string, string> }) {
  const sha = data.label
  const url = `https://github.com/furyfist/Sentinel/commit/${sha}`
  return (
    <div className="bg-blue-600 text-white rounded-lg px-3 py-2 shadow-md min-w-[140px] text-xs">
      <Handle type="target" position={Position.Left} className="!bg-blue-300" />
      <div className="font-mono font-bold text-blue-100 text-[10px] mb-0.5">commit</div>
      <a href={url} target="_blank" rel="noopener noreferrer"
        className="font-semibold underline decoration-blue-300 hover:decoration-white transition-colors"
        onClick={e => e.stopPropagation()}
      >{sha}</a>
      {data.detail && <div className="text-blue-200 mt-0.5 line-clamp-2">{data.detail}</div>}
      {data.author && <div className="text-blue-300 text-[10px] mt-1">@{data.author}</div>}
      <Handle type="source" position={Position.Right} className="!bg-blue-300" />
    </div>
  )
}
