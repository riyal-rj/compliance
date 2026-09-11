import logging
import uuid

from backend.src.models.audit import AuditRequest, AuditResponse
from backend.src.services.audit_service import ComplianceWorkflowService

logger = logging.getLogger(__name__)

class AuditController:
    """Coordinates audit requests without depending on the web framework."""

    def __init__(self, service: ComplianceWorkflowService | None = None) -> None:
        self._service= service or ComplianceWorkflowService()

    def audit_video(self, request: AuditRequest) -> AuditResponse:
        session_id = str(uuid.uuid4())
        logger.info("Received Audit Request: %s (Session: %s)", request.video_url, session_id)

        try:
            return self._service.run_audit(request.video_url, session_id)
        except Exception as exc:
            logger.error("Audit Failed (Session: %s)", session_id)
            raise