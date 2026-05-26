import type { IncidentReport, RiskHistory, DigestEntry, HealthStatus, Settings, CurrentRisk, CommitDetail, LoopDetection, TraceGraph, WorstTrace } from '@/types'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`PUT ${path} failed: ${res.status}`)
  return res.json()
}

export const api = {
  health: () => get<HealthStatus>('/health'),

  incidents: {
    list: (limit = 20) => get<IncidentReport[]>(`/incidents?limit=${limit}`),
    get: (id: number) => get<IncidentReport>(`/incidents/${id}`),
  },

  risk: {
    history: (limit = 50) => get<RiskHistory[]>(`/risk/history?limit=${limit}`),
    current: (pr: number) => get<CurrentRisk>(`/risk/current/${pr}`),
  },

  digest: {
    latest: () => get<DigestEntry>('/digest/latest'),
    history: (limit = 20) => get<DigestEntry[]>(`/digest/history?limit=${limit}`),
  },

  settings: {
    get: () => get<Settings>('/settings'),
    update: (data: Settings) => put<Settings>('/settings', data),
  },

  commits: {
    get: (shas: string[]) => get<CommitDetail[]>(`/commits?shas=${shas.join(',')}`),
  },

  loops: {
    active: () => get<LoopDetection[]>('/loops/active'),
    history: (limit = 50) => get<LoopDetection[]>(`/loops/history?limit=${limit}`),
    fingerprint: (traceId: string) => get<Record<string, unknown>>(`/loops/${traceId}/fingerprint`),
  },

  forensics: {
    traceGraph: (traceId: string) => get<TraceGraph>(`/forensics/trace/${traceId}`),
    incidentGraph: (start: string, end: string) => get<TraceGraph>(`/forensics/incident?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`),
    worstTraces: (limit = 10) => get<WorstTrace[]>(`/forensics/worst-traces?limit=${limit}`),
  },
}
