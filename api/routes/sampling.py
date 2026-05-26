from fastapi import APIRouter
from agent import memory

router = APIRouter()

DEFAULT_POLICY = {
    "has_error_score": 100,
    "cost_spike_score": 80,
    "schema_failed_score": 70,
    "novel_pattern_score": 60,
    "high_gen_score": 40,
    "keep_threshold": 40,
}

_policy = dict(DEFAULT_POLICY)


@router.get("/sampling/stats")
def sampling_stats():
    rows = memory.get_sampling_stats(limit=1)
    if not rows:
        return {"total_traces": 0, "sampled_traces": 0, "dropped_traces": 0, "keep_reasons": {}, "recorded_at": None}
    latest = rows[0]
    import json
    keep_reasons = latest.get("keep_reasons") or {}
    if isinstance(keep_reasons, str):
        try:
            keep_reasons = json.loads(keep_reasons)
        except Exception:
            keep_reasons = {}
    return {
        "total_traces": latest.get("total_traces", 0),
        "sampled_traces": latest.get("sampled_traces", 0),
        "dropped_traces": latest.get("dropped_traces", 0),
        "keep_reasons": keep_reasons,
        "recorded_at": latest.get("recorded_at"),
    }


@router.get("/sampling/policy")
def get_policy():
    return _policy


@router.put("/sampling/policy")
def update_policy(body: dict):
    for k, v in body.items():
        if k in DEFAULT_POLICY:
            _policy[k] = v
    return _policy
