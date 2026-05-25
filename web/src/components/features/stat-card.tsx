'use client'

import { motion } from 'framer-motion'

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  accent?: 'default' | 'green' | 'red' | 'amber' | 'indigo'
  delay?: number
}

const accents = {
  default: 'text-slate-900',
  green:   'text-emerald-600',
  red:     'text-red-500',
  amber:   'text-amber-500',
  indigo:  'text-indigo-600',
}

export function StatCard({ label, value, sub, accent = 'default', delay = 0 }: StatCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.25, 0.46, 0.45, 0.94] }}
      className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow"
    >
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
      <p className={`text-2xl font-semibold mt-2 tabular-nums ${accents[accent]}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </motion.div>
  )
}
