# FastAPI route handlers live here; they validate request inputs, call services, and return response schemas.
from __future__ import annotations

import mimetypes
from pathlib import Path
import re
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

from app.core.config import get_settings
from app.integrations.object_storage import get_object_storage
from app.services.asset_delivery import AssetDeliveryService


router = APIRouter()


def _is_allowed_download_origin(origin: str) -> bool:
    settings = get_settings()
    allowed_origins = {
        *settings.cors_origins,
        settings.frontend_base_url,
    }
    if origin in allowed_origins:
        return True
    parsed = urlparse(origin)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {"localhost", "127.0.0.1", "::1"}


def _download_cors_headers(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin", "").strip()
    if not origin:
        return {}
    if not _is_allowed_download_origin(origin):
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": request.headers.get("access-control-request-headers", "*"),
        "Vary": "Origin",
    }


@router.options("/download")
async def download_asset_options(request: Request) -> Response:
    return Response(status_code=204, headers=_download_cors_headers(request))


@router.options("/download/{filename:path}")
async def download_asset_with_filename_options(request: Request) -> Response:
    return Response(status_code=204, headers=_download_cors_headers(request))


async def _download_asset_response(
    request: Request,
    token: str,
    filename: str | None,
    download: bool | None,
) -> FileResponse:
    delivery = AssetDeliveryService()
    storage = get_object_storage()
    try:
        payload = delivery.verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        absolute_path = storage.absolute_path(str(payload["storage_path"]))
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - storage providers surface backend-specific errors
        raise HTTPException(status_code=404, detail="Asset not found") from exc

    path = Path(absolute_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    resolved_filename = str(filename or payload.get("filename") or path.name)
    resolved_filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "-", resolved_filename).strip(" .") or path.name
    media_type = mimetypes.guess_type(resolved_filename)[0] or "application/octet-stream"
    disposition = "attachment" if (bool(payload.get("download")) or bool(download)) else "inline"
    return FileResponse(
        absolute_path,
        media_type=media_type,
        filename=resolved_filename,
        content_disposition_type=disposition,
        headers=_download_cors_headers(request),
    )


@router.get("/download")
async def download_asset(
    request: Request,
    token: str = Query(..., min_length=1),
    filename: str | None = Query(default=None),
    download: bool | None = Query(default=None),
) -> FileResponse:
    # Serves the download asset endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    return await _download_asset_response(request, token, filename, download)


@router.get("/download/{filename:path}")
async def download_asset_with_filename(
    request: Request,
    filename: str,
    token: str = Query(..., min_length=1),
    download: bool | None = Query(default=None),
) -> FileResponse:
    return await _download_asset_response(request, token, filename, download)
