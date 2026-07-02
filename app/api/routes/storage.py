# FastAPI route handlers live here; they validate request inputs, call services, and return response schemas.
from __future__ import annotations

import mimetypes
from pathlib import Path
import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.integrations.object_storage import LocalObjectStorage
from app.services.asset_delivery import AssetDeliveryService


router = APIRouter()


@router.get("/download")
async def download_asset(
    token: str = Query(..., min_length=1),
    filename: str | None = Query(default=None),
    download: bool | None = Query(default=None),
) -> FileResponse:
    # Serves the download asset endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    delivery = AssetDeliveryService()
    storage = LocalObjectStorage()
    try:
        payload = delivery.verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        absolute_path = storage.absolute_path(str(payload["storage_path"]))
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

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
    )
