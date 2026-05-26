export interface IncidentReport {
  id: number
  detected_at: string
  detection_type: string | null
  severity: string | null
  report_text: string | null
  related_commits: string[]
  related_errors: string[]
  cost_impact: number
  slack_thread_ts: string | null
}

export interface RiskHistory {
  id: number
  file_path: string
  commit_sha: string | null
  change_date: string
  cost_delta: number
  error_delta: number
  risk_score: number
}

export interface DigestEntry {
  id: number
  detected_at: string
  report_text: string | null
  cost_impact: number
}

export interface HealthStatus {
  status: string
  coral: boolean
}

export interface Settings {
  cost_spike_multiplier: number
  pr_risk_threshold: number
  agent_loop_generation_threshold: number
  error_cascade_threshold: number
}

export interface CurrentRisk {
  pr_number: number
  risk_score: number
  files_changed: string[]
  file_count: number
}

export interface CommitDetail {
  sha: string
  message: string | null
  author: string | null
  url: string
}

export interface LoopDetection {
  id: number
  trace_id: string
  detected_at: string
  loop_count: number
  cost_burned: number
  tool_pattern: string | null
  status: string
  kill_method: string | null
  slack_ts: string | null
}
