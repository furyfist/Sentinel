import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_OWNER = os.environ.get("GITHUB_OWNER", "furyfist")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "Sentinel")

LANGFUSE_BASE_URL = os.environ.get("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")
LANGFUSE_PUBLIC_KEY = os.environ["LANGFUSE_PUBLIC_KEY"]
LANGFUSE_SECRET_KEY = os.environ["LANGFUSE_SECRET_KEY"]

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_INCIDENTS_CHANNEL = os.environ.get("SLACK_INCIDENTS_CHANNEL", "#incidents")

COST_SPIKE_MULTIPLIER = float(os.environ.get("COST_SPIKE_MULTIPLIER", "2.5"))
PR_RISK_THRESHOLD = int(os.environ.get("PR_RISK_THRESHOLD", "70"))
AGENT_LOOP_GENERATION_THRESHOLD = int(os.environ.get("AGENT_LOOP_GENERATION_THRESHOLD", "10"))
ERROR_CASCADE_THRESHOLD = float(os.environ.get("ERROR_CASCADE_THRESHOLD", "10.0"))
