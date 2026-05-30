'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { ReactFlow, MiniMap, Controls, Background, BackgroundVariant } from '@xyflow/react'
import { api } from '@/lib/api'
import { NODE_TYPES } from '@/components/features/graph'
import { autoLayout } from '@/lib/graph-layout'
import type { CommitDetail, IncidentReport, TraceGraph } from '@/types'

const severityStyles: Record<string, string> = {
  high:   'bg-red-50 text-red-600 border-red-200',
  medium: 'bg-amber-50 text-amber-600 border-amber-200',
  info:   'bg-sky-50 text-sky-600 border-sky-200',
  low:    'bg-slate-50 text-slate-600 border-slate-200',
}

type Tab = 'report' | 'graph'

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [incident, setIncident] = useState<IncidentReport | null>(null)
  const [commits, setCommits] = useState<CommitDetail[]>([])
  const [commitsLoading, setCommitsLoading] = useState(false)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<Tab>('report')
  const [graph, setGraph] = useState<TraceGraph | null>(null)
  const [graphLoading, setGraphLoading] = useState(false)

  useEffect(() => {
    api.incidents.get(Number(id))
      .then((inc) => {
        setIncident(inc)
        if (inc.related_commits.length > 0) {
          setCommitsLoading(true)
          api.commits.get(inc.related_commits).then(setCommits).catch(() => {}).finally(() => setCommitsLoading(false))
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  const loadGraph = useCallback(async (inc: IncidentReport) => {
    if (graph) return
    setGraphLoading(true)
    const detected = inc.detected_at
    // Normalize SQLite UTC timestamps (space format, no tz) before parsing
    const normalized = detected.replace(' ', 'T').replace(/(\.\d{3})\d+/, '$1')
    const hasTz = /Z$|[+-]\d{2}:\d{2}$/.test(normalized)
    const detectedMs = new Date(hasTz ? normalized : normalized + 'Z').getTime()
    const start = new Date(detectedMs - 2 * 60 * 60 * 1000).toISOString()
    const end = new Date(detectedMs + 2 * 60 * 60 * 1000).toISOString()
    try {
      const data = await api.forensics.incidentGraph(start, end)
      setGraph({ ...data, nodes: autoLayout(data.nodes, data.edges, 'horizontal') })
    } catch {
      setGraph({ nodes: [], edges: [], error: 'Failed to load graph' })
    } finally {
      setGraphLoading(false)
    }
  }, [graph])

  const handleTabChange = (t: Tab) => {
    setTab(t)
    if (t === 'graph' && incident) loadGraph(incident)
  }

  if (loading) {
    return <div className="space-y-4">{[...Array(4)].map((_, i) => <div key={i} className="h-16 bg-white rounded-xl border border-slate-200 animate-pulse" />)}</div>
  }

  if (!incident) {
    return (
      <div className="text-center py-20 text-slate-400">
        Incident not found. <Link href="/incidents" className="text-indigo-500 underline">Back to list</Link>
      </div>
    )
  }

  const badgeStyle = severityStyles[incident.severity ?? 'info'] ?? severityStyles.info
  const commitMap = Object.fromEntries(commits.map((c) => [c.sha, c]))
  const githubBase = `https://github.com/furyfist/Sentinel/commit`

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="space-y-6">
      <div>
        <Link href="/incidents" className="text-sm text-indigo-500 hover:text-indigo-700 transition-colors">← Back to Incidents</Link>
        <div className="flex items-center gap-3 mt-3">
          <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize ${badgeStyle}`}>
            {incident.severity ?? 'info'}
          </span>
          <span className="text-xs text-slate-400">{incident.detection_type} · {(() => { const s = incident.detected_at.replace(' ', 'T'); return new Date(/Z$|[+-]\d{2}:\d{2}$/.test(s) ? s : s + 'Z').toLocaleString() })()}</span>
        </div>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {(['report', 'graph'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => handleTabChange(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition-colors border-b-2 -mb-px ${
              tab === t ? 'border-indigo-500 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {t === 'graph' ? 'Dependency Graph' : 'Report'}
          </button>
        ))}
      </div>

      {tab === 'report' && (
        <>
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Incident Report</h2>
            <div className="prose prose-sm prose-slate max-w-none
              [&>p]:text-slate-700 [&>p]:leading-relaxed [&>p]:mb-3
              [&>ol]:text-slate-700 [&>ol]:space-y-2 [&>ol]:pl-4
              [&>ul]:text-slate-700 [&>ul]:space-y-2 [&>ul]:pl-4
              [&_li]:leading-relaxed [&_strong]:text-slate-800 [&_strong]:font-semibold
              [&>h1]:text-base [&>h1]:font-semibold [&>h1]:text-slate-800 [&>h1]:mb-2
              [&>h2]:text-sm [&>h2]:font-semibold [&>h2]:text-slate-700 [&>h2]:mb-1.5
              [&>h3]:text-sm [&>h3]:font-semibold [&>h3]:text-slate-700 [&>h3]:mb-1">
              <ReactMarkdown>{incident.report_text ?? ''}</ReactMarkdown>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {incident.related_commits.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Related Commits</h3>
                <div className="space-y-2">
                  {commitsLoading
                    ? incident.related_commits.map((sha) => (
                        <div key={sha} className="flex items-center gap-2.5 bg-slate-50 border border-slate-100 px-3 py-2 rounded-lg">
                          <span className="font-mono text-xs text-indigo-400">{sha.slice(0, 7)}</span>
                          <div className="h-3 flex-1 bg-slate-200 rounded animate-pulse" />
                        </div>
                      ))
                    : incident.related_commits.map((sha) => {
                        const detail = commitMap[sha]
                        const url = detail?.url ?? `${githubBase}/${sha}`
                        return (
                          <a key={sha} href={url} target="_blank" rel="noopener noreferrer"
                            className="flex items-start gap-2.5 bg-slate-50 hover:bg-indigo-50 border border-slate-100 hover:border-indigo-200 px-3 py-2 rounded-lg transition-colors group">
                            <span className="font-mono text-xs text-indigo-600 shrink-0 mt-0.5 group-hover:text-indigo-700">{sha.slice(0, 7)}</span>
                            <span className="text-xs text-slate-600 leading-relaxed truncate">{detail?.message ?? sha.slice(0, 20)}</span>
                          </a>
                        )
                      })}
                </div>
              </div>
            )}
            {incident.related_errors.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Related Errors</h3>
                <div className="space-y-1.5">
                  {incident.related_errors.map((err, i) => (
                    <span key={i} className="block text-xs bg-red-50 text-red-600 px-3 py-1.5 rounded-lg border border-red-100">{err}</span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {incident.cost_impact > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
              <span className="text-red-500 font-semibold text-lg">${incident.cost_impact.toFixed(2)}/hr</span>
              <span className="text-sm text-red-600">cost impact at time of detection</span>
            </div>
          )}
        </>
      )}

      {tab === 'graph' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden" style={{ height: 520 }}>
          {graphLoading && (
            <div className="h-full flex items-center justify-center text-sm text-slate-400">Loading graph…</div>
          )}
          {graph?.error && (
            <div className="h-full flex items-center justify-center text-sm text-red-400">{graph.error}</div>
          )}
          {!graphLoading && graph && !graph.error && (graph.nodes?.length ?? 0) > 0 && (
            <ReactFlow nodes={graph.nodes} edges={graph.edges} nodeTypes={NODE_TYPES} fitView fitViewOptions={{ padding: 0.2 }}>
              <MiniMap />
              <Controls />
              <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#e2e8f0" />
            </ReactFlow>
          )}
          {!graphLoading && graph && !graph.error && (graph.nodes?.length ?? 0) === 0 && (
            <div className="h-full flex items-center justify-center text-sm text-slate-400">No graph data for this incident window</div>
          )}
        </div>
      )}
    </motion.div>
  )
}
