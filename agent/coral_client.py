import subprocess
import json


def query(sql: str, timeout: int = 30) -> list[dict]:
    result = subprocess.run(
        ["coral", "sql", "--format", "json", sql],
        capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(f"Coral query failed: {result.stderr.strip()}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Coral returned invalid JSON: {e}\nOutput: {result.stdout[:300]}")
    if not isinstance(data, list):
        raise RuntimeError(f"Expected JSON array, got: {type(data)}")
    return data
