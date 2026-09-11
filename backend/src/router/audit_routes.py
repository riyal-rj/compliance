import logging

from fastapi import APIRouter, HTTPException

from backend.src.controllers.audit_controller import AuditController
from backend.src.models.audit import AuditRequest, AuditResponse

logger = logging.getLogger(__name__)
router = APIRouter()
controller = AuditController()

@router.post("/audit", response_model=AuditResponse)
async def audit_video(request: AuditRequest) -> AuditResponse:
    try:
        return controller.audit_video(request)
    except Exception as exc:
        logger.error("Workflow execution failed: %s", exc)
        raise HTTPException(status_code=500,
                            detail=f"Workflow Excution Failed: {exc}") from exc

@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status":  "healthy",
        "service": "Brand Guardian AI"
    }
