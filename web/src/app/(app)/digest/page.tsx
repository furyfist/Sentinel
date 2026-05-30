'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import { DigestSection } from '@/components/features/digest-section'
import type { DigestEntry } from '@/types'

export default function DigestPage() {
  const [digests, setDigests] = useState<DigestEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.digest.history().then(setDigests).finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <h1 className="text-2xl font-semibold text-slate-900">Weekly Digests</h1>
        <p className="text-sm text-slate-500 mt-0.5">What shipped, what broke, what to watch</p>
      </motion.div>

      {loading ? (
        <div className="space-y-4">
          {[...Array(2)].map((_, i) => <div key={i} className="h-48 bg-white rounded-xl border border-slate-200 animate-pulse" />)}
        </div>
      ) : digests.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-sm text-slate-400">
          No digests yet — run the Weekly Digest mode to generate one
        </div>
      ) : (
        <div className="space-y-4">
          {digests.map((digest, i) => (
            <motion.div
              key={digest.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: i * 0.08 }}
            >
              <DigestSection digest={digest} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
