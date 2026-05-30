'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { RiskBadge } from '@/components/features/risk-badge'
import type { RiskHistory } from '@/types'

export default function RiskPage() {
  const [history, setHistory] = useState<RiskHistory[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.risk.history().then(setHistory).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <h1 className="text-2xl font-semibold text-slate-900">PR Risk History</h1>
        <p className="text-sm text-slate-500 mt-0.5">File-level risk based on historical error and cost correlation</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden"
      >
        {loading ? (
          <div className="p-6 space-y-3">
            {[...Array(5)].map((_, i) => <div key={i} className="h-10 bg-slate-50 rounded-lg animate-pulse" />)}
          </div>
        ) : history.length === 0 ? (
          <div className="p-12 text-center text-sm text-slate-400">No risk history yet — run the PR Risk Scorer on a pull request</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">File</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Risk Score</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Errors</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Cost Delta</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Date</th>
              </tr>
            </thead>
            <tbody>
              {history.map((row, i) => (
                <motion.tr
                  key={row.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.04 }}
                  className="border-b border-slate-50 hover:bg-slate-50 transition-colors"
                >
                  <td className="px-5 py-3 font-mono text-xs text-slate-600 max-w-[240px] truncate">{row.file_path}</td>
                  <td className="px-5 py-3"><RiskBadge score={row.risk_score} size="sm" /></td>
                  <td className="px-5 py-3 text-slate-600">{row.error_delta}</td>
                  <td className="px-5 py-3 text-slate-600">${row.cost_delta.toFixed(4)}</td>
                  <td className="px-5 py-3 text-slate-400 text-xs">{new Date(row.change_date).toLocaleDateString()}</td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        )}
      </motion.div>
    </div>
  )
}
