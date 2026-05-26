'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { StatCard } from '@/components/features/stat-card'
import { IncidentCard } from '@/components/features/incident-card'
import { DigestSection } from '@/components/features/digest-section'
import type { IncidentReport, DigestEntry, HealthStatus, LoopDetection, SamplingStats } from '@/types'

export default function DashboardPage() {
  const [incidents, setIncidents] = useState<IncidentReport[]>([])
  const [digest, setDigest] = useState<DigestEntry | null>(null)
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [activeLoops, setActiveLoops] = useState<LoopDetection[]>([])
  const [sampling, setSampling] = useState<SamplingStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      api.incidents.list(5).then(setIncidents),
      api.digest.latest().then(setDigest).catch(() => {}),
      api.health().then(setHealth),
      api.loops.active().then(setActiveLoops).catch(() => {}),
      api.sampling.stats().then(setSampling).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  const totalCost = incidents.reduce((s, i) => s + i.cost_impact, 0)
  const highCount = incidents.filter((i) => i.severity === 'high').length
  const loopCount = activeLoops.length
  const worstLoop = activeLoops[0] ?? null

  return (
    <div className="space-y-8">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
            <p className="text-sm text-slate-500 mt-0.5">Engineering observability at a glance</p>
          </div>
          {health && (
            <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-full px-3 py-1.5 shadow-sm">
              <span className={`w-2 h-2 rounded-full ${health.coral ? 'bg-emerald-400' : 'bg-red-400'} animate-pulse`} />
              <span className="text-xs text-slate-500 font-medium">
                Coral {health.coral ? 'connected' : 'offline'}
              </span>
            </div>
          )}
        </div>
      </motion.div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total Incidents" value={loading ? '—' : incidents.length} delay={0.05} />
        <StatCard label="Peak Cost / hr" value={loading ? '—' : `$${totalCost.toFixed(2)}`} accent="red" delay={0.1} />
        <StatCard label="High Severity" value={loading ? '—' : highCount} accent={highCount > 0 ? 'red' : 'green'} delay={0.15} />
        <StatCard
          label="Active Loops"
          value={loading ? '—' : loopCount}
          accent={loopCount > 0 ? 'red' : 'green'}
          sub={worstLoop ? `${worstLoop.trace_id.slice(0, 8)} · $${(worstLoop.cost_burned ?? 0).toFixed(4)}` : undefined}
          delay={0.2}
        />
      </div>

      {!loading && sampling && sampling.total_traces > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.22 }}
          className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm"
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Sampling Efficiency</h2>
            <span className="text-xs text-slate-400">last run</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="flex items-end gap-1.5 mb-1">
                <span className="text-2xl font-bold text-slate-900">{sampling.sampled_traces}</span>
                <span className="text-sm text-slate-400 pb-0.5">of {sampling.total_traces} traces analyzed</span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5">
                <div
                  className="bg-indigo-500 h-1.5 rounded-full"
                  style={{ width: `${Math.round((sampling.sampled_traces / sampling.total_traces) * 100)}%` }}
                />
              </div>
              <p className="text-xs text-slate-400 mt-1">
                {Math.round((sampling.dropped_traces / sampling.total_traces) * 100)}% noise dropped
              </p>
            </div>
            <div className="flex flex-col gap-1 shrink-0 text-xs text-slate-500">
              {sampling.keep_reasons.has_error != null && sampling.keep_reasons.has_error > 0 && (
                <span>{sampling.keep_reasons.has_error} errors</span>
              )}
              {sampling.keep_reasons.cost_spike != null && sampling.keep_reasons.cost_spike > 0 && (
                <span>{sampling.keep_reasons.cost_spike} cost spikes</span>
              )}
              {sampling.keep_reasons.novel_pattern != null && sampling.keep_reasons.novel_pattern > 0 && (
                <span>{sampling.keep_reasons.novel_pattern} novel patterns</span>
              )}
              {sampling.keep_reasons.high_gen != null && sampling.keep_reasons.high_gen > 0 && (
                <span>{sampling.keep_reasons.high_gen} high-gen</span>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {loopCount > 0 && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.25 }}
          className="bg-red-50 border border-red-200 rounded-xl p-4"
        >
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <h2 className="text-sm font-semibold text-red-700">
              {loopCount} Active Loop{loopCount > 1 ? 's' : ''} Detected
            </h2>
          </div>
          <div className="space-y-2">
            {activeLoops.slice(0, 3).map((loop) => (
              <div key={loop.id} className="flex items-center justify-between bg-white rounded-lg border border-red-100 px-4 py-2.5">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs text-slate-500">{loop.trace_id.slice(0, 12)}…</span>
                  <span className="text-xs text-slate-600">{loop.loop_count} generations</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${
                    loop.status === 'active' ? 'bg-red-50 text-red-600 border-red-200' : 'bg-slate-50 text-slate-500 border-slate-200'
                  }`}>{loop.status}</span>
                </div>
                <span className="text-sm font-semibold text-red-500">${(loop.cost_burned ?? 0).toFixed(4)}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-3">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Recent Incidents</h2>
          {loading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-24 bg-white rounded-xl border border-slate-200 animate-pulse" />
              ))}
            </div>
          ) : incidents.length === 0 ? (
            <EmptyState label="No incidents yet" />
          ) : (
            <div className="space-y-3">
              {incidents.map((inc, i) => <IncidentCard key={inc.id} incident={inc} index={i} />)}
            </div>
          )}
        </div>

        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Latest Digest</h2>
          {loading ? (
            <div className="h-64 bg-white rounded-xl border border-slate-200 animate-pulse" />
          ) : digest ? (
            <DigestSection digest={digest} compact />
          ) : (
            <EmptyState label="No digest yet" />
          )}
        </div>
      </div>
    </div>
  )
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-sm text-slate-400">
      {label}
    </div>
  )
}
