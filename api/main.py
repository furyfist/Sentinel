from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import incidents, risk, digest, settings, commits
from api.routes import slack_actions, loops, quality, forensics
from agent import coral_client

app = FastAPI(title="Sentinel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents.router, prefix="/api")
app.include_router(risk.router, prefix="/api")
app.include_router(digest.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(commits.router, prefix="/api")
app.include_router(slack_actions.router, prefix="/api/slack")
app.include_router(loops.router, prefix="/api")
app.include_router(quality.router, prefix="/api")
app.include_router(forensics.router, prefix="/api")


@app.get("/api/health")
def health():
    try:
        coral_client.query("SELECT 1 as ping")
        coral_ok = True
    except Exception:
        coral_ok = False
    return {"status": "ok", "coral": coral_ok}
