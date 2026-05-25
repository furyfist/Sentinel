'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { IncidentCard } from '@/components/features/incident-card'
import type { IncidentReport } from '@/types'

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentReport[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.incidents.list(50).then(setIncidents).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <h1 className="text-2xl font-semibold text-slate-900">Incidents</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          {loading ? 'Loading…' : `${incidents.length} incident${incidents.length !== 1 ? 's' : ''} recorded`}
        </p>
      </motion.div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 bg-white rounded-xl border border-slate-200 animate-pulse" />
          ))}
        </div>
      ) : incidents.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-sm text-slate-400">
          No incidents recorded yet
        </div>
      ) : (
        <div className="space-y-3">
          {incidents.map((inc, i) => <IncidentCard key={inc.id} incident={inc} index={i} />)}
        </div>
      )}
    </div>
  )
}
