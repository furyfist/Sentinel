import json
from agent.config import GROQ_API_KEY, GROQ_MODEL

_client = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def _call(system: str, user: str, max_tokens: int = 1000) -> str:
    response = _get_client().chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content


_INCIDENT_SYSTEM = (
    "You are Sentinel, an engineering observability agent. "
    "Write a concise incident report from the data provided. "
    "Be specific: name the commits, error titles, cost figures, and timestamps. "
    "Structure: 1) What happened 2) Likely cause 3) Impact 4) Recommended action. "
    "No fluff. Plain English. Under 300 words."
)


def narrate_incident(sql_results: dict, detection_type: str) -> str:
    user = (
        f"Detection type: {detection_type}\n"
        f"Data:\n{json.dumps(sql_results, indent=2, default=str)}\n\n"
        "Write the incident report."
    )
    return _call(_INCIDENT_SYSTEM, user)


_PR_RISK_SYSTEM = (
    "You are Sentinel, a PR risk analyst. "
    "Given a risk score and the historical record of what happened after similar file changes, "
    "write one short paragraph explaining why this PR is risky or safe. "
    "Be specific: reference file names, past error counts, cost deltas. "
    "End with a one-line recommendation. Under 150 words."
)


def narrate_pr_risk(file_history: list, risk_score: int) -> str:
    user = (
        f"Risk score: {risk_score}/100\n"
        f"File change history:\n{json.dumps(file_history, indent=2, default=str)}\n\n"
        "Write the risk summary."
    )
    return _call(_PR_RISK_SYSTEM, user, max_tokens=400)


_DIGEST_SYSTEM = (
    "You are Sentinel, an engineering weekly digest writer. "
    "Write a structured digest with exactly three sections:\n"
    "## What Shipped\n## What Broke\n## What to Watch\n"
    "Be specific: PR titles, error counts, cost trends, percentages. "
    "Each section: 2-4 bullet points. Under 400 words total."
)


def narrate_weekly_digest(shipped: list, errors: list, cost_trend: list) -> str:
    user = (
        f"PRs merged this week:\n{json.dumps(shipped, indent=2, default=str)}\n\n"
        f"Sentry errors this week:\n{json.dumps(errors, indent=2, default=str)}\n\n"
        f"Langfuse cost trend:\n{json.dumps(cost_trend, indent=2, default=str)}\n\n"
        "Write the weekly digest."
    )
    return _call(_DIGEST_SYSTEM, user, max_tokens=800)
