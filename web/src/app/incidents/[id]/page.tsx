'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { api } from '@/lib/api'
import type { IncidentReport } from '@/types'

const severityStyles: Record<string, string> = {
  high:   'bg-red-50 text-red-600 border-red-200',
  medium: 'bg-amber-50 text-amber-600 border-amber-200',
  info:   'bg-sky-50 text-sky-600 border-sky-200',
  low:    'bg-slate-50 text-slate-600 border-slate-200',
}

export default function IncidentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [incident, setIncident] = useState<IncidentReport | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.incidents.get(Number(id)).then(setIncident).catch(() => {}).finally(() => setLoading(false))
  }, [id])

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

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="space-y-6">
      <div>
        <Link href="/incidents" className="text-sm text-indigo-500 hover:text-indigo-700 transition-colors">← Back to Incidents</Link>
        <div className="flex items-center gap-3 mt-3">
          <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize ${badgeStyle}`}>
            {incident.severity ?? 'info'}
          </span>
          <span className="text-xs text-slate-400">{incident.detection_type} · {new Date(incident.detected_at).toLocaleString()}</span>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Incident Report</h2>
        <div className="prose prose-sm prose-slate max-w-none
          [&>p]:text-slate-700 [&>p]:leading-relaxed [&>p]:mb-3
          [&>ol]:text-slate-700 [&>ol]:space-y-2 [&>ol]:pl-4
          [&>ul]:text-slate-700 [&>ul]:space-y-2 [&>ul]:pl-4
          [&_li]:leading-relaxed
          [&_strong]:text-slate-800 [&_strong]:font-semibold
          [&>h1]:text-base [&>h1]:font-semibold [&>h1]:text-slate-800 [&>h1]:mb-2
          [&>h2]:text-sm [&>h2]:font-semibold [&>h2]:text-slate-700 [&>h2]:mb-1.5
          [&>h3]:text-sm [&>h3]:font-semibold [&>h3]:text-slate-700 [&>h3]:mb-1">
          <ReactMarkdown>{incident.report_text}</ReactMarkdown>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {incident.related_commits.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Related Commits</h3>
            <div className="space-y-1.5">
              {incident.related_commits.map((sha) => (
                <span key={sha} className="block font-mono text-xs bg-slate-50 text-slate-600 px-3 py-1.5 rounded-lg border border-slate-100">{sha.slice(0, 12)}</span>
              ))}
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
    </motion.div>
  )
}
