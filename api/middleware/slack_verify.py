import hashlib
import hmac
import time
from fastapi import Request, HTTPException


async def verify_slack_signature(request: Request, signing_secret: str) -> bytes:
    """
    Verify incoming Slack request using HMAC-SHA256.
    Rejects replayed requests older than 5 minutes.
    Returns the raw request body for downstream parsing.
    """
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not timestamp or not signature:
        raise HTTPException(status_code=403, detail="Missing Slack headers")

    if abs(time.time() - int(timestamp)) > 300:
        raise HTTPException(status_code=403, detail="Request too old")

    body = await request.body()
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed = "v0=" + hmac.new(
        signing_secret.encode(), sig_basestring.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    return body
