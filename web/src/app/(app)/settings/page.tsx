'use client'

import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { api } from '@/lib/api'
import type { Settings } from '@/types'

const FIELDS: { key: keyof Settings; label: string; description: string; step: number }[] = [
  { key: 'cost_spike_multiplier',          label: 'Cost Spike Multiplier',          description: 'Alert when hourly cost exceeds this multiple of the 7-day avg', step: 0.1 },
  { key: 'pr_risk_threshold',              label: 'PR Risk Threshold',              description: 'Auto-request changes when risk score exceeds this (0–100)',      step: 1   },
  { key: 'agent_loop_generation_threshold',label: 'Agent Loop Threshold',           description: 'Alert when a single trace exceeds this many generations/hr',     step: 1   },
  { key: 'error_cascade_threshold',        label: 'Error Cascade Threshold',        description: 'Alert when error_count × retry_cost exceeds this value',         step: 0.5 },
]

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.settings.get().then(setSettings).finally(() => setLoading(false))
  }, [])

  const handleChange = (key: keyof Settings, value: string) => {
    if (!settings) return
    setSettings({ ...settings, [key]: parseFloat(value) })
    setSaved(false)
  }

  const handleSave = async () => {
    if (!settings) return
    setSaving(true)
    await api.settings.update(settings)
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <h1 className="text-2xl font-semibold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-500 mt-0.5">Configure Sentinel detection thresholds</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="bg-white rounded-xl border border-slate-200 shadow-sm divide-y divide-slate-100"
      >
        {loading ? (
          <div className="p-6 space-y-4">
            {[...Array(4)].map((_, i) => <div key={i} className="h-16 bg-slate-50 rounded-lg animate-pulse" />)}
          </div>
        ) : settings ? (
          FIELDS.map(({ key, label, description, step }) => (
            <div key={key} className="flex items-center justify-between gap-6 px-6 py-4">
              <div className="flex-1">
                <p className="text-sm font-medium text-slate-800">{label}</p>
                <p className="text-xs text-slate-400 mt-0.5">{description}</p>
              </div>
              <input
                type="number"
                step={step}
                value={settings[key]}
                onChange={(e) => handleChange(key, e.target.value)}
                className="w-24 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-mono text-slate-800 text-right focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent transition"
              />
            </div>
          ))
        ) : null}
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="flex items-center gap-3"
      >
        <button
          onClick={handleSave}
          disabled={saving || !settings}
          className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors shadow-sm"
        >
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
        {saved && (
          <motion.span
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            className="text-sm text-emerald-600 font-medium"
          >
            Saved
          </motion.span>
        )}
      </motion.div>
    </div>
  )
}
