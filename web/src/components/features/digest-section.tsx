'use client'

import { motion } from 'framer-motion'
import type { DigestEntry } from '@/types'

interface DigestSectionProps {
  digest: DigestEntry
  compact?: boolean
}

function renderMarkdown(text: string) {
  return text.split('\n').map((line, i) => {
    if (line.startsWith('## '))
      return <h3 key={i} className="text-sm font-semibold text-slate-700 mt-4 mb-1.5 first:mt-0">{line.replace('## ', '')}</h3>
    if (line.startsWith('* ') || line.startsWith('- '))
      return <li key={i} className="text-sm text-slate-600 ml-3">{line.slice(2)}</li>
    if (line.trim() === '') return null
    return <p key={i} className="text-sm text-slate-600">{line}</p>
  })
}

export function DigestSection({ digest, compact = false }: DigestSectionProps) {
  const date = new Date(digest.detected_at).toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm"
    >
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">{date}</p>
        {digest.cost_impact > 0 && (
          <span className="text-xs text-red-500 font-medium">${digest.cost_impact.toFixed(2)} cost</span>
        )}
      </div>
      <ul className={`space-y-0.5 ${compact ? 'line-clamp-6' : ''}`}>
        {renderMarkdown(digest.report_text ?? '')}
      </ul>
    </motion.div>
  )
}
