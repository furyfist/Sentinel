'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'

export default function QualityPage() {
  const [snapshots, setSnapshots] = useState<Record<string, unknown>[]>([])
  const [drift, setDrift] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.allSettled([
      api.quality.snapshots().then(setSnapshots).catch(() => {}),
      api.quality.drift().then(setDrift).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Quality</h1>
        <p className="text-sm text-slate-500 mt-1">Prompt drift detection and schema validation</p>
      </div>

      <section>
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Drift Events</h2>
        {loading ? (
          <div className="h-24 bg-white rounded-xl border border-slate-200 animate-pulse" />
        ) : drift.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-sm text-slate-400">
            No drift detected
          </div>
        ) : (
          <div className="space-y-2">
            {drift.map((e, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-xl px-4 py-3 flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-slate-800">{String(e.feature_name ?? '—')}</span>
                  <span className="ml-3 text-xs text-slate-400">{String(e.drift_type ?? '')}</span>
                  {e.validation_fail_rate != null && (
                    <span className="ml-3 text-xs text-slate-400">fail rate: {(Number(e.validation_fail_rate) * 100).toFixed(0)}%</span>
                  )}
                  {e.blame_commit_sha ? (
                    <span className="ml-3 text-xs font-mono text-slate-400" title={String(e.blame_commit_message ?? '')}>
                      {String(e.blame_commit_sha).slice(0, 8)} — {String(e.blame_commit_message ?? '').slice(0, 60)}
                    </span>
                  ) : null}
                </div>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-lg border ${
                  e.severity === 'critical' ? 'bg-red-50 text-red-700 border-red-200' :
                  e.severity === 'high' ? 'bg-orange-50 text-orange-700 border-orange-200' :
                  'bg-yellow-50 text-yellow-700 border-yellow-200'
                }`}>{String(e.severity ?? 'unknown')}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Schema Snapshots</h2>
        {loading ? (
          <div className="h-24 bg-white rounded-xl border border-slate-200 animate-pulse" />
        ) : snapshots.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-sm text-slate-400">
            No snapshots captured yet
          </div>
        ) : (
          <div className="space-y-2">
            {snapshots.map((s, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-xl px-4 py-3 flex items-center justify-between">
                <span className="text-sm font-medium text-slate-800">{String(s.feature_name ?? '—')}</span>
                <span className="text-xs text-slate-400 font-mono">{String(s.captured_at ?? '').slice(0, 16)}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
