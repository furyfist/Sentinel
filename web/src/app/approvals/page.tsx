'use client'

import { useEffect, useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import type { ApprovalItem } from '@/types'

const TABS = ['pending', 'approved', 'rejected', 'expired'] as const
type Tab = typeof TABS[number]

const TAB_LABELS: Record<Tab, string> = {
  pending: 'Pending',
  approved: 'Approved',
  rejected: 'Rejected',
  expired: 'Expired',
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-700 border-red-200',
  high: 'bg-orange-100 text-orange-700 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  low: 'bg-slate-100 text-slate-600 border-slate-200',
}

function parseDate(iso: string): Date {
  // Normalize SQLite space format and truncate microseconds to milliseconds
  const normalized = iso.replace(' ', 'T').replace(/(\.\d{3})\d+/, '$1')
  // Treat as UTC if no timezone info present
  const withTz = /[Z+\-]\d*$/.test(normalized) ? normalized : normalized + 'Z'
  return new Date(withTz)
}

function timeAgo(iso: string) {
  const diff = Date.now() - parseDate(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

function timeRemaining(iso: string | null) {
  if (!iso) return null
  const diff = parseDate(iso).getTime() - Date.now()
  if (diff <= 0) return 'Expired'
  const m = Math.floor(diff / 60000)
  if (m < 60) return `${m}m left`
  return `${Math.floor(m / 60)}h left`
}

export default function ApprovalsPage() {
  const [tab, setTab] = useState<Tab>('pending')
  const [items, setItems] = useState<ApprovalItem[]>([])
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<number | null>(null)

  const load = useCallback(async (status: Tab) => {
    setLoading(true)
    try {
      const data = await api.approvals.list(status)
      setItems(data)
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(tab) }, [tab, load])

  const handleApprove = async (id: number) => {
    setActing(id)
    try {
      await api.approvals.approve(id)
      setItems(prev => prev.filter(i => i.id !== id))
    } catch {
    } finally {
      setActing(null)
    }
  }

  const handleReject = async (id: number) => {
    setActing(id)
    try {
      await api.approvals.reject(id)
      setItems(prev => prev.filter(i => i.id !== id))
    } catch {
    } finally {
      setActing(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-slate-900">Approvals</h1>
        <p className="text-sm text-slate-500 mt-1">Human-in-the-loop governance queue</p>
      </div>

      <div className="flex gap-1 mb-6 bg-slate-100 p-1 rounded-lg w-fit">
        {TABS.map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`relative px-4 py-1.5 text-sm rounded-md font-medium transition-colors ${
              tab === t ? 'text-slate-900' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab === t && (
              <motion.span
                layoutId="approvals-tab"
                className="absolute inset-0 bg-white rounded-md shadow-sm"
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative">{TAB_LABELS[t]}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-sm text-slate-400 py-12 text-center">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-slate-400 py-12 text-center">
          No {TAB_LABELS[tab].toLowerCase()} approvals
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(item => {
            const severityClass = SEVERITY_COLORS[item.severity ?? 'low'] ?? SEVERITY_COLORS.low
            const summary = typeof item.context?.summary === 'string'
              ? item.context.summary
              : JSON.stringify(item.context).slice(0, 200)
            const remaining = timeRemaining(item.expires_at)

            return (
              <div key={item.id} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${severityClass}`}>
                        {item.severity ?? 'unknown'}
                      </span>
                      <span className="text-xs font-mono text-slate-500">{item.action_type}</span>
                      {item.anomaly_type && (
                        <span className="text-xs text-slate-400">{item.anomaly_type}</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-700 leading-snug line-clamp-3">{summary}</p>
                    <div className="flex items-center gap-3 mt-2 text-[11px] text-slate-400">
                      <span>{timeAgo(item.created_at)}</span>
                      {remaining && tab === 'pending' && (
                        <span className={remaining === 'Expired' ? 'text-red-400' : 'text-slate-400'}>
                          {remaining}
                        </span>
                      )}
                      {item.resolved_by && (
                        <span>by {item.resolved_by}</span>
                      )}
                      {item.resolved_at && (
                        <span>resolved {timeAgo(item.resolved_at)}</span>
                      )}
                    </div>
                  </div>

                  {tab === 'pending' && (
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => handleApprove(item.id)}
                        disabled={acting === item.id}
                        className="px-3 py-1.5 text-xs font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReject(item.id)}
                        disabled={acting === item.id}
                        className="px-3 py-1.5 text-xs font-medium bg-white text-red-600 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
                      >
                        Reject
                      </button>
                    </div>
                  )}

                  {tab !== 'pending' && (
                    <span className={`shrink-0 text-xs font-semibold px-2 py-1 rounded-lg ${
                      item.status === 'approved' ? 'bg-green-50 text-green-700' :
                      item.status === 'rejected' ? 'bg-red-50 text-red-700' :
                      'bg-slate-100 text-slate-500'
                    }`}>
                      {item.status}
                    </span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
