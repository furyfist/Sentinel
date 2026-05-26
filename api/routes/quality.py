from fastapi import APIRouter, HTTPException, BackgroundTasks
from agent import memory, coral_client
from agent.detectors.drift_detector import DriftDetector

router = APIRouter()


@router.get("/quality/snapshots")
def get_snapshots():
    return memory.get_all_schema_snapshots()


@router.get("/quality/drift")
def get_drift_events(limit: int = 20):
    return memory.get_drift_events(limit=limit)


@router.post("/quality/scan")
def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger a drift scan in the background. Returns immediately."""
    background_tasks.add_task(_run_scan)
    return {"status": "scan_started"}


def _run_scan():
    from agent.modes.drift_patrol import run
    try:
        run(dry_run=False)
    except Exception as e:
        print(f"[quality/scan] error: {e}")


@router.get("/quality/feature/{name}/validation")
def get_feature_validation(name: str):
    try:
        detector = DriftDetector(coral_client, memory)
        observations = detector.get_recent_outputs(name, limit=20)
        if not observations:
            raise HTTPException(status_code=404, detail=f"No observations found for feature '{name}'")
        return detector.validate_observations(name, observations)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
