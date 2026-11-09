import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", summary="Liveness probe", description="Check if the service is alive")
async def liveness() -> dict[str, str]:
    logger.info("Liveness check requested")
    return {"status": "alive"}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Check if the service is ready to serve requests",
)
async def readiness() -> dict[str, str]:
    logger.info("Readiness check requested")
    return {"status": "ready"}
