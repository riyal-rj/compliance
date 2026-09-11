from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional, cast

from backend.src.models.audit import ComplianceIssue, AuditResponse
from backend.src.workflow.workflow import app as compliance_workflow

logger = logging.getLogger(__name__)

class ComplianceWorkflowService:
    """Service layer orchestrating the compliance workflow and reponse mapping."""

    def __init__(self, graph: Any | None = None) -> None:
        self._graph = graph or compliance_workflow

    def build_initial_state(self,
                            video_url: str,
                            session_id: Optional[str] = None) -> Dict[str, Any]:
        session_id = session_id or str(uuid.uuid4())
        video_id = f"vid_{session_id[:8]}"
        return {
            "video_url": video_url,
            "video_id": video_id,
            "compliance_results": [],
            "errors":[],
        }

    def _map_compliance_result(self, results: Any) -> list[ComplianceIssue]:
        normalized: list[ComplianceIssue] = []

        for issue in results or []:
            if isinstance(issue, ComplianceIssue):
                normalized.append(issue)
                continue

            normalized.append(
                ComplianceIssue(
                    category = str(issue.get("category", "General")),
                    severity = str(issue.get("severity", "UNKNOWN")),
                    description = str(issue.get("description", "No descirption provided")),
                )
            )

        return normalized

    def run_audit(self, 
                   video_url: str,
                   session_id: Optional[str] = None) -> AuditResponse:
        session_id = session_id or str(uuid.uuid4())
        initial_inputs = self.build_initial_state(video_url, 
                                                  session_id)
        logger.info("Starting Audit Session %s", session_id)
        final_state = self._graph.invoke(cast(Any, initial_inputs))

        compliance_results = self._map_compliance_result(final_state.get("compliance_results",[]))  

        return AuditResponse(
            session_id = session_id,
            video_id = final_state.get("video_id", initial_inputs["video_id"]),
            status = final_state.get("final_status", "UNKNOWN"),
            final_report = final_state.get("final_report", "No report generated"),
            compliance_results = compliance_results
        )

# def run_cli_simulation(self, video_url: str = "https://youtu.be")

def create_workflow_service() -> ComplianceWorkflowService:
    return ComplianceWorkflowService()