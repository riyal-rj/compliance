from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field

class AuditRequest(BaseModel):
    "Imncoming API request payload for a compliance result."

    video_url: str

class ComplianceIssue(BaseModel):
    "Single compliance finding returned by the audit workflow."

    category: str
    severity: str
    description: str

class AuditResponse(BaseModel):
    """HTTP response model for the audit endpoint."""

    session_id: str
    video_id: str
    status: str
    final_report: str
    compliance_results: List[ComplianceIssue] = Field(default_factory=list)