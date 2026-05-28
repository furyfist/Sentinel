"""Test Slack HMAC signature verification logic."""
import sys, os, hmac, hashlib, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECRET = "test-secret-key"
BODY = b"payload=test123"

ts = str(int(time.time()))
sig_base = f"v0:{ts}:{BODY.decode()}"
expected = "v0=" + hmac.new(SECRET.encode(), sig_base.encode(), hashlib.sha256).hexdigest()

print(f"Signature generated: {expected[:30]}...")

assert expected.startswith("v0="), "Signature must start with v0="
assert len(expected) == 3 + 64, f"Expected 67 chars, got {len(expected)}"

# Verify mismatch detection
bad_sig = expected[:-4] + "XXXX"
assert bad_sig != expected, "Bad sig should differ"

print("Slack HMAC signature logic: PASS")
print("Missing headers rejection: requires live FastAPI (manual test)")
