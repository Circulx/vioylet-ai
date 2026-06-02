from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse, Response

from app.integrations.object_storage import get_object_storage
from app.services.asset_delivery import AssetDeliveryService


router = APIRouter()


@router.get("/download")
async def download_asset(token: str = Query(..., min_length=1)) -> Response:
    delivery = AssetDeliveryService()
    storage = get_object_storage()
    try:
        payload = delivery.verify_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    filename = str(payload.get("filename") or Path(str(payload["storage_path"])).name)
    disposition = "attachment" if bool(payload.get("download")) else "inline"
    presigned_url = getattr(storage, "presigned_url", None)
    if callable(presigned_url):
        try:
            url = presigned_url(
                str(payload["storage_path"]),
                filename=filename,
                download=bool(payload.get("download")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return RedirectResponse(url, status_code=307)

    try:
        absolute_path = storage.absolute_path(str(payload["storage_path"]))
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    path = Path(absolute_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Asset not found")

    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    return FileResponse(
        absolute_path,
        media_type=media_type,
        filename=filename,
        content_disposition_type=disposition,
    )
