import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import incidents, risk, digest, settings, commits
from api.routes import slack_actions, loops, quality, forensics, approvals, sampling
from agent import coral_client

app = FastAPI(title="Sentinel API", version="1.0.0")

_allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_frontend_url = os.environ.get("FRONTEND_URL", "")
if _frontend_url:
    _allowed_origins.append(_frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes"):
    try:
        from scripts.seed_demo_sqlite import (
            _already_seeded, seed_incidents, seed_loops, seed_approvals,
            seed_drift, seed_sampling, seed_file_risk,
        )
        if not _already_seeded():
            seed_incidents(); seed_loops(); seed_approvals()
            seed_drift(); seed_sampling(); seed_file_risk()
            print("[demo] seed complete")
    except Exception as e:
        print(f"[demo seed] warning: {e}")

app.include_router(incidents.router, prefix="/api")
app.include_router(risk.router, prefix="/api")
app.include_router(digest.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(commits.router, prefix="/api")
app.include_router(slack_actions.router, prefix="/api/slack")
app.include_router(loops.router, prefix="/api")
app.include_router(quality.router, prefix="/api")
app.include_router(forensics.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(sampling.router, prefix="/api")


@app.get("/api/health")
def health():
    try:
        coral_client.query("SELECT 1 as ping")
        coral_ok = True
    except Exception:
        coral_ok = False
    return {"status": "ok", "coral": coral_ok}
