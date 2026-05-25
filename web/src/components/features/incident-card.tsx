'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import type { IncidentReport } from '@/types'

interface IncidentCardProps {
  incident: IncidentReport
  index?: number
}

const severityStyles: Record<string, string> = {
  high:   'bg-red-50 text-red-600 border-red-200',
  medium: 'bg-amber-50 text-amber-600 border-amber-200',
  info:   'bg-sky-50 text-sky-600 border-sky-200',
  low:    'bg-slate-50 text-slate-600 border-slate-200',
}

function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/#{1,6}\s+/g, '')
    .replace(/^\d+\.\s+/gm, '')
    .replace(/^[-*]\s+/gm, '')
    .replace(/\n+/g, ' ')
    .trim()
}

export function IncidentCard({ incident, index = 0 }: IncidentCardProps) {
  const severity = incident.severity ?? 'info'
  const badgeStyle = severityStyles[severity] ?? severityStyles.info
  const date = new Date(incident.detected_at).toLocaleString()
  const preview = incident.report_text
    ? stripMarkdown(incident.report_text).slice(0, 140)
    : '—'

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.06, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      <Link href={`/incidents/${incident.id}`}>
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all cursor-pointer group">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold capitalize ${badgeStyle}`}>
                  {severity}
                </span>
                <span className="text-xs text-slate-400">{incident.detection_type ?? 'unknown'}</span>
              </div>
              <p className="text-sm text-slate-600 line-clamp-2">{preview}</p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-xs text-slate-400">{date}</p>
              {incident.cost_impact > 0 && (
                <p className="text-sm font-semibold text-red-500 mt-1">
                  ${incident.cost_impact.toFixed(2)}/hr
                </p>
              )}
            </div>
          </div>
          {incident.related_commits.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {incident.related_commits.slice(0, 3).map((sha) => (
                <span key={sha} className="font-mono text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
                  {sha.slice(0, 7)}
                </span>
              ))}
            </div>
          )}
        </div>
      </Link>
    </motion.div>
  )
}
