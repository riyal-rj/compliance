from __future__ import annotations

import logging
import os

from azure.monitor.opentelemetry import configure_azure_monitor

from backend.src.config.env_config import envConfig

logger = logging.getLogger(__name__)
_configured = False

def setup_telemetry() -> None:
    """Configure Azure monitor OpenTelemetry before the FastAPI app starts."""
    global _configured

    if _configured:
        return

    connection_string = envConfig.azure_application_insights_connection_str
    if not connection_string:
        logger.warning("APPLICATIONINSIGHTS_CONNECTION_STRING is not set; telemetry is disabled.")
        return


    try:

        configure_azure_monitor(
            connection_string = connection_string,
            logger_name = "brand-guardian-tracer",
        )
        logger.info("Azure Monitor Tracking Enabled & Connected!")
    except Exception as exc:
        logger.error(f"Failed to initialize Azure Monitor: {exc}")
        

