"""FastAPI main application."""

from fastapi import FastAPI

from app.api.v1 import router as api_v1_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="Professional FastAPI service for cryptocurrency market data and technical indicators",
    version="0.1.0",
)


@app.get("/")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "message": f"{settings.app_name} is running"}


# Include API routes
app.include_router(api_v1_router, prefix=settings.api_prefix)

logger.info(f"{settings.app_name} started successfully")
