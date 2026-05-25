'use client'

import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import type { DigestEntry } from '@/types'

interface DigestSectionProps {
  digest: DigestEntry
  compact?: boolean
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
      <div className={`prose prose-sm prose-slate max-w-none
        [&>p]:text-slate-600 [&>p]:leading-relaxed [&>p]:mb-2
        [&>ul]:text-slate-600 [&>ul]:space-y-1 [&>ul]:pl-4
        [&>ol]:text-slate-600 [&>ol]:space-y-1 [&>ol]:pl-4
        [&_li]:leading-relaxed
        [&_strong]:text-slate-800 [&_strong]:font-semibold
        [&>h2]:text-sm [&>h2]:font-semibold [&>h2]:text-slate-700 [&>h2]:mt-4 [&>h2]:mb-1.5 [&>h2]:first:mt-0
        [&>h3]:text-sm [&>h3]:font-semibold [&>h3]:text-slate-700 [&>h3]:mt-3 [&>h3]:mb-1
        ${compact ? 'line-clamp-6' : ''}`}>
        <ReactMarkdown>{digest.report_text ?? ''}</ReactMarkdown>
      </div>
    </motion.div>
  )
}
