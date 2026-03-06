from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter()


@router.get("/health", tags=["ops"])
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": "0.1.0"})


@router.get("/metrics", tags=["ops"], include_in_schema=False)
async def metrics() -> Response:
    """Prometheus metrics scrape endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
