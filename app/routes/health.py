from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health", tags=["ops"])
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "version": "0.1.0"})
