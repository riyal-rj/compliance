from __future__ import annotations

import logging

from fastapi import FastAPI

from backend.src.api.azure_telemetry import setup_telemetry
from backend.src.router.audit_routes import router as audit_router

logger = logging.getLogger("brand-guardian-app")

def create_app() -> FastAPI:
    "Factory used to build the application with MVCS structure"

    setup_telemetry()

    app = FastAPI(
        title="Brand Guardian AI API",
        description="API for auditing video content against brand compliance rules.",
        version="1.0.0",
    )

    app.include_router(audit_router)
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.src.app_factory:app", host="0.0.0.0", port=8000, reload=True)
