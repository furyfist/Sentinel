"""Scores traces and decides keep vs drop — retains actionable signal, drops routine noise."""
from __future__ import annotations

import json


class SmartSampler:
    """
    Scoring rules:
      has_error (level ERROR/WARNING)  → +100
      cost > 2× average                → +80
      schema validation failed         → +70
      novel tool pattern               → +60
      generation count > 5             → +40
      routine successful trace         → +0

    Keep threshold: score >= 40
    """

    def __init__(self, memory=None, keep_threshold: int = 40):
        self.memory = memory
        self.keep_threshold = keep_threshold
        self._seen_patterns: set[str] = set()
        self.avg_cost: float = 0.0
        self._load_baseline()

    def _load_baseline(self):
        if not self.memory:
            return
        try:
            baselines = self.memory.get_baselines(limit=168)
            if baselines:
                costs = [b.get("hourly_cost", 0) or 0 for b in baselines]
                total_gens = sum(b.get("generation_count", 1) or 1 for b in baselines)
                total_cost = sum(costs)
                if total_gens:
                    self.avg_cost = total_cost / total_gens
        except Exception:
            pass

    def _is_novel_pattern(self, tool_names: list[str]) -> bool:
        if not tool_names:
            return False
        key = json.dumps(sorted(tool_names))
        if key in self._seen_patterns:
            return False
        self._seen_patterns.add(key)
        return True

    def score_trace(self, trace_data: dict) -> int:
        score = 0
        if trace_data.get("has_error") or str(trace_data.get("level", "")).upper() in ("ERROR", "WARNING"):
            score += 100
        cost = float(trace_data.get("total_cost") or trace_data.get("cost") or 0)
        if self.avg_cost > 0 and cost > self.avg_cost * 2:
            score += 80
        if trace_data.get("schema_failed"):
            score += 70
        tool_names = trace_data.get("tool_names") or []
        if isinstance(tool_names, str):
            try:
                tool_names = json.loads(tool_names)
            except Exception:
                tool_names = []
        if self._is_novel_pattern(tool_names):
            score += 60
        gen_count = int(trace_data.get("gen_count") or trace_data.get("generation_count") or 0)
        if gen_count > 5:
            score += 40
        return score

    def filter_traces(self, traces: list[dict]) -> tuple[list[dict], list[dict]]:
        kept, dropped = [], []
        for t in traces:
            if self.score_trace(t) >= self.keep_threshold:
                kept.append(t)
            else:
                dropped.append(t)
        return kept, dropped

    def get_reason_breakdown(self, kept: list[dict]) -> dict:
        reasons = {"has_error": 0, "cost_spike": 0, "schema_failed": 0, "novel_pattern": 0, "high_gen": 0}
        for t in kept:
            if t.get("has_error") or str(t.get("level", "")).upper() in ("ERROR", "WARNING"):
                reasons["has_error"] += 1
            cost = float(t.get("total_cost") or t.get("cost") or 0)
            if self.avg_cost > 0 and cost > self.avg_cost * 2:
                reasons["cost_spike"] += 1
            if t.get("schema_failed"):
                reasons["schema_failed"] += 1
            gen_count = int(t.get("gen_count") or t.get("generation_count") or 0)
            if gen_count > 5:
                reasons["high_gen"] += 1
        return reasons
