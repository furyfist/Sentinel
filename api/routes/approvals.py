from fastapi import APIRouter, HTTPException
from agent import memory
from agent.governance.approval_gate import ApprovalGate

router = APIRouter()


@router.get("/approvals")
def list_approvals(status: str = None, limit: int = 50):
    return memory.get_approvals(status=status, limit=limit)


@router.get("/approvals/stats")
def approval_stats():
    all_items = memory.get_approvals(limit=1000)
    counts = {"pending": 0, "approved": 0, "rejected": 0, "expired": 0}
    resolution_times = []

    for item in all_items:
        s = item.get("status", "pending")
        if s in counts:
            counts[s] += 1
        if item.get("resolved_at") and item.get("created_at"):
            try:
                from datetime import datetime
                created = datetime.fromisoformat(item["created_at"])
                resolved = datetime.fromisoformat(item["resolved_at"])
                resolution_times.append((resolved - created).total_seconds() / 60)
            except Exception:
                pass

    avg = sum(resolution_times) / len(resolution_times) if resolution_times else None
    return {**counts, "avg_resolution_minutes": avg}


@router.post("/approvals/{approval_id}/approve")
def approve_item(approval_id: int):
    approval = memory.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Approval is already {approval['status']}")

    gate = ApprovalGate(memory=memory)
    gate.execute_action_for_approval(approval)
    memory.update_approval(approval_id, status="approved", resolved_by="web_ui")
    return memory.get_approval(approval_id)


@router.post("/approvals/{approval_id}/reject")
def reject_item(approval_id: int):
    approval = memory.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Approval is already {approval['status']}")

    memory.update_approval(approval_id, status="rejected", resolved_by="web_ui")
    return memory.get_approval(approval_id)
