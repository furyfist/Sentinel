'use client'

import { useEffect, useState, useCallback } from 'react'
import { ReactFlow, MiniMap, Controls, Background, BackgroundVariant } from '@xyflow/react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { NODE_TYPES } from '@/components/features/graph'
import { autoLayout } from '@/lib/graph-layout'
import type { TraceGraph, WorstTrace } from '@/types'

export default function ForensicsPage() {
  const [worstTraces, setWorstTraces] = useState<WorstTrace[]>([])
  const [graph, setGraph] = useState<TraceGraph | null>(null)
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'trace' | 'incident'>('trace')
  const [loading, setLoading] = useState(false)
  const [sidebarLoading, setSidebarLoading] = useState(true)

  useEffect(() => {
    api.forensics.worstTraces(10).then(setWorstTraces).catch(() => {}).finally(() => setSidebarLoading(false))
  }, [])

  const loadTraceGraph = useCallback(async (traceId: string) => {
    setSelectedTrace(traceId)
    setViewMode('trace')
    setLoading(true)
    try {
      const data = await api.forensics.traceGraph(traceId)
      setGraph({ ...data, nodes: autoLayout(data.nodes, data.edges, 'vertical') })
    } catch {
      setGraph({ nodes: [], edges: [], error: 'Failed to load trace graph' })
    } finally {
      setLoading(false)
    }
  }, [])

  const loadIncidentGraph = useCallback(async (trace: WorstTrace) => {
    setViewMode('incident')
    setLoading(true)
    const start = new Date(new Date(trace.started_at).getTime() - 2 * 60 * 60 * 1000).toISOString()
    const end = new Date(new Date(trace.started_at).getTime() + 2 * 60 * 60 * 1000).toISOString()
    try {
      const data = await api.forensics.incidentGraph(start, end)
      setGraph({ ...data, nodes: autoLayout(data.nodes, data.edges, 'horizontal') })
    } catch {
      setGraph({ nodes: [], edges: [], error: 'Failed to load incident graph' })
    } finally {
      setLoading(false)
    }
  }, [])

  const nodes = graph?.nodes ?? []
  const edges = graph?.edges ?? []

  return (
    <div className="space-y-4">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <h1 className="text-2xl font-semibold text-slate-900">Forensics</h1>
        <p className="text-sm text-slate-500 mt-0.5">Trace dependency graphs and cross-source incident timelines</p>
      </motion.div>

      <div className="flex gap-4 h-[calc(100vh-220px)] min-h-[500px]">
        <div className="w-64 shrink-0 flex flex-col gap-2 overflow-y-auto">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest px-1">Worst Traces</div>
          {sidebarLoading ? (
            [...Array(5)].map((_, i) => <div key={i} className="h-16 bg-white rounded-lg border border-slate-200 animate-pulse" />)
          ) : worstTraces.length === 0 ? (
            <div className="text-xs text-slate-400 px-1">No traces found</div>
          ) : (
            worstTraces.map((t) => (
              <button
                key={t.trace_id}
                onClick={() => loadTraceGraph(t.trace_id)}
                className={`text-left rounded-lg border p-3 text-xs transition-all ${
                  selectedTrace === t.trace_id
                    ? 'border-indigo-300 bg-indigo-50 shadow-sm'
                    : 'border-slate-200 bg-white hover:border-indigo-200 hover:bg-slate-50'
                }`}
              >
                <div className="font-mono text-slate-500 text-[10px]">{t.trace_id.slice(0, 12)}…</div>
                <div className="font-semibold text-slate-800 mt-0.5">${(t.total_cost ?? 0).toFixed(4)}</div>
                <div className="text-slate-400 mt-0.5">{t.observation_count} obs · {t.error_count} err</div>
              </button>
            ))
          )}
        </div>

        <div className="flex-1 flex flex-col gap-2">
          {selectedTrace && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => setViewMode('trace')}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  viewMode === 'trace' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-300'
                }`}
              >
                Trace Graph
              </button>
              <button
                onClick={() => {
                  const t = worstTraces.find((x) => x.trace_id === selectedTrace)
                  if (t) loadIncidentGraph(t)
                }}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  viewMode === 'incident' ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-300'
                }`}
              >
                View Incident Graph
              </button>
            </div>
          )}

          <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
            {loading && (
              <div className="absolute inset-0 bg-white/70 flex items-center justify-center z-10">
                <div className="text-sm text-slate-500">Loading graph…</div>
              </div>
            )}
            {!graph && !loading && (
              <div className="h-full flex items-center justify-center text-sm text-slate-400">
                Select a trace from the sidebar
              </div>
            )}
            {graph?.error && (
              <div className="h-full flex items-center justify-center text-sm text-red-400">{graph.error}</div>
            )}
            {nodes.length > 0 && (
              <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={NODE_TYPES}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.2}
              >
                <MiniMap nodeColor={(n) => NODE_COLOR[n.type ?? 'event'] ?? '#94a3b8'} className="!bottom-4 !right-4" />
                <Controls className="!bottom-4 !left-4" />
                <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e2e8f0" />
              </ReactFlow>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

const NODE_COLOR: Record<string, string> = {
  commit: '#4f46e5',
  error: '#ef4444',
  trace: '#f59e0b',
  message: '#14b8a6',
  generation: '#8b5cf6',
  span: '#0ea5e9',
  event: '#94a3b8',
}
