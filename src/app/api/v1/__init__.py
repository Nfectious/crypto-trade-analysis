"""API v1 routes initialization."""

from fastapi import APIRouter

from app.api.v1 import routes_live_data, ws_live_data

router = APIRouter()
router.include_router(routes_live_data.router)
router.include_router(ws_live_data.router)
