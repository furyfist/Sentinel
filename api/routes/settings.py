import json
import os
from fastapi import APIRouter
from api.models import Settings

router = APIRouter(prefix="/settings", tags=["settings"])

_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "settings.json",
)

_DEFAULTS = {
    "cost_spike_multiplier": 2.5,
    "pr_risk_threshold": 70,
    "agent_loop_generation_threshold": 10,
    "error_cascade_threshold": 10.0,
}


def _load() -> dict:
    if os.path.exists(_SETTINGS_FILE):
        with open(_SETTINGS_FILE) as f:
            return {**_DEFAULTS, **json.load(f)}
    return _DEFAULTS.copy()


def _save(data: dict) -> None:
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


@router.get("", response_model=Settings)
def get_settings():
    return Settings(**_load())


@router.put("", response_model=Settings)
def update_settings(payload: Settings):
    _save(payload.model_dump())
    return payload
