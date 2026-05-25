from pydantic import BaseModel
from typing import Optional
import json


class IncidentReport(BaseModel):
    id: int
    detected_at: str
    detection_type: Optional[str]
    severity: Optional[str]
    report_text: Optional[str]
    related_commits: list[str] = []
    related_errors: list[str] = []
    cost_impact: float = 0.0
    slack_thread_ts: Optional[str]

    @classmethod
    def from_row(cls, row: dict) -> "IncidentReport":
        return cls(
            **{**row,
               "related_commits": json.loads(row.get("related_commits") or "[]"),
               "related_errors": json.loads(row.get("related_errors") or "[]")}
        )


class RiskHistory(BaseModel):
    id: int
    file_path: str
    commit_sha: Optional[str]
    change_date: str
    cost_delta: float = 0.0
    error_delta: int = 0
    risk_score: float = 0.0


class DigestEntry(BaseModel):
    id: int
    detected_at: str
    report_text: Optional[str]
    cost_impact: float = 0.0


class HealthStatus(BaseModel):
    status: str
    coral: bool


class Settings(BaseModel):
    cost_spike_multiplier: float
    pr_risk_threshold: int
    agent_loop_generation_threshold: int
    error_cascade_threshold: float
