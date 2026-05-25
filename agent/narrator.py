import json
from groq import Groq
from agent.config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def _call(system: str, user: str, max_tokens: int = 1000) -> str:
    response = _client.chat.completions.create(
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
