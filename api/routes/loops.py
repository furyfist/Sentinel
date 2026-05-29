from fastapi import APIRouter, HTTPException
from agent import memory, coral_client
from agent.detectors.loop_detector import LoopDetector
from agent.config import SLACK_INCIDENTS_CHANNEL

router = APIRouter()


@router.get("/loops/detect")
def run_loop_detection():
    try:
        detector = LoopDetector(coral_client, memory)
        loops = detector.detect_loops()
        for loop in loops:
            detector.fire_loop_alert(loop, SLACK_INCIDENTS_CHANNEL)
        return loops
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/loops/active")
def get_active_loops():
    return memory.get_loop_detections(status="active")


@router.get("/loops/history")
def get_loop_history(limit: int = 50):
    return memory.get_loop_detections(limit=limit)


@router.get("/loops/{trace_id}/fingerprint")
def get_loop_fingerprint(trace_id: str):
    try:
        detector = LoopDetector(coral_client)
        return detector.fingerprint_loop(trace_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
