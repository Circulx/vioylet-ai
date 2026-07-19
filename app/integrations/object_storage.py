# Integration adapters keep storage and vector search details behind small project-facing interfaces.
from __future__ import annotations

import contextlib
from dataclasses import dataclass
import mimetypes
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID
from uuid import uuid4

from app.core.config import get_settings
from app.utils.files import ensure_parent, sanitize_filename


@dataclass(slots=True)
class StoredObject:
    # Adapter class for stored object; it hides backend-specific storage or search behavior from the service
    # layer.
    storage_path: str
    absolute_path: str


class ObjectStorage(Protocol):
    # Adapter class for object storage; it hides backend-specific storage or search behavior from the service
    # layer.
    # Builds relative path through the adapter boundary, letting services use one interface across local and
    # external backends.
    def build_relative_path(
        self,
        tenant_id: UUID,
        brand_space_id: UUID | None,
        category: str,
        filename: str,
    ) -> str: ...

    # Handles save bytes through the adapter boundary, letting services use one interface across local and
    # external backends.
    def save_bytes(
        self,
        tenant_id: UUID,
        brand_space_id: UUID | None,
        category: str,
        filename: str,
        content: bytes,
    ) -> StoredObject: ...

    # Handles read bytes through the adapter interface so service code stays backend-agnostic.
    def read_bytes(self, storage_path: str) -> bytes: ...
    # Handles exists through the adapter interface so service code stays backend-agnostic.
    def exists(self, storage_path: str) -> bool: ...
    # Deletes a stored object through the adapter contract so service code stays backend-agnostic.
    def delete(self, storage_path: str) -> None: ...
    # Handles absolute path through the adapter interface so service code stays backend-agnostic.
    def absolute_path(self, storage_path: str) -> str: ...


class ObjectStoragePathMixin:
    # Adapter class for object storage path mixin; it hides backend-specific storage or search behavior from the
    # service layer.
    @staticmethod
    def _safe_segment(value: str, *, fallback: str) -> str:
        # Handles safe segment through the adapter boundary, letting services use one interface across local and
        # external backends.
        cleaned = sanitize_filename(value, fallback=fallback, max_length=80)
        return cleaned.replace(".", "-").strip("-") or fallback

    def _generate_object_name(self, filename: str) -> str:
        # Generates object name through the adapter boundary, letting services use one interface across local
        # and external backends.
        cleaned = sanitize_filename(filename, fallback="file", max_length=96)
        suffix = Path(cleaned).suffix.lower()
        stem = Path(cleaned).stem or "file"
        return f"{stem[:48]}-{uuid4().hex}{suffix}"

    def build_relative_path(
        self,
        tenant_id: UUID,
        brand_space_id: UUID | None,
        category: str,
        filename: str,
    ) -> str:
        # Builds relative path through the adapter boundary, letting services use one interface across local and
        # external backends.
        brand_component = str(brand_space_id) if brand_space_id else "global"
        category_parts = [part for part in str(category or "").replace("\\", "/").split("/") if part.strip()]
        safe_parts = [self._safe_segment(part, fallback="files") for part in category_parts] or ["files"]
        object_name = self._generate_object_name(filename)
        category_path = "/".join(safe_parts)
        return f"{tenant_id}/{brand_component}/{category_path}/{object_name}"


class LocalObjectStorage(ObjectStoragePathMixin):
    # Adapter class for local object storage; it hides backend-specific storage or search behavior from the
    # service layer.
    def __init__(self) -> None:
        # Captures adapter settings once so later storage or vector calls can stay focused on the operation.
        self.settings = get_settings()
        self.base_path = Path(self.settings.object_storage_base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_storage_path(self, storage_path: str) -> Path:
        # Resolves storage path through the adapter boundary, letting services use one interface across local
        # and external backends.
        resolved = (self.base_path / storage_path).resolve()
        try:
            resolved.relative_to(self.base_path)
        except ValueError:
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Storage path validation failed:")
            logger.error(f"  Base path: {self.base_path}")
            logger.error(f"  Storage path: {storage_path}")
            logger.error(f"  Resolved path: {resolved}")
            raise ValueError("Resolved storage path is outside the configured storage root")
        return resolved

    def save_bytes(
        self,
        tenant_id: UUID,
        brand_space_id: UUID | None,
        category: str,
        filename: str,
        content: bytes,
    ) -> StoredObject:
        # Handles save bytes through the adapter boundary, letting services use one interface across local and
        # external backends.
        relative_path = self.build_relative_path(tenant_id, brand_space_id, category, filename)
        absolute_path = self._resolve_storage_path(relative_path)
        ensure_parent(absolute_path)
        absolute_path.write_bytes(content)
        return StoredObject(storage_path=relative_path, absolute_path=str(absolute_path))

    def read_bytes(self, storage_path: str) -> bytes:
        # Handles read bytes through the adapter boundary, letting services use one interface across local and
        # external backends.
        return self._resolve_storage_path(storage_path).read_bytes()

    def exists(self, storage_path: str) -> bool:
        # Handles exists through the adapter boundary, letting services use one interface across local and
        # external backends.
        try:
            return self._resolve_storage_path(storage_path).exists()
        except ValueError:
            return False

    def delete(self, storage_path: str) -> None:
        # Deletes the stored object through the adapter boundary, letting services use one interface across local and
        # external backends.
        path = self._resolve_storage_path(storage_path)
        if path.exists():
            path.unlink()

    def absolute_path(self, storage_path: str) -> str:
        # Handles absolute path through the adapter boundary, letting services use one interface across local
        # and external backends.
        return str(self._resolve_storage_path(storage_path))


class S3ObjectStorage(ObjectStoragePathMixin):
    # Adapter class for s3 object storage; it hides backend-specific storage or search behavior from the service
    # layer.
    def __init__(self) -> None:
        # Captures adapter settings once so later storage or vector calls can stay focused on the operation.
        self.settings = get_settings()
        self.bucket = str(self.settings.aws_s3_bucket or "").strip()
        if not self.bucket:
            raise RuntimeError("AWS_S3_BUCKET is required when OBJECT_STORAGE_PROVIDER=s3")
        self.prefix = str(self.settings.aws_s3_prefix or "").strip().strip("/")
        self.cache_path = Path(self.settings.object_storage_cache_path).resolve()
        self.cache_path.mkdir(parents=True, exist_ok=True)
        try:
            import boto3  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("boto3 is required when OBJECT_STORAGE_PROVIDER=s3") from exc
        client_kwargs: dict[str, Any] = {}
        if self.settings.aws_region:
            client_kwargs["region_name"] = self.settings.aws_region
        self.client = boto3.client("s3", **client_kwargs)

    @staticmethod
    def _normalize_storage_path(storage_path: str) -> str:
        # Normalizes storage path through the adapter boundary, letting services use one interface across local
        # and external backends.
        normalized = str(storage_path or "").replace("\\", "/").strip().strip("/")
        if not normalized:
            raise ValueError("Storage path is empty")
        parts = [part for part in normalized.split("/") if part]
        if any(part in {".", ".."} for part in parts):
            raise ValueError("Storage path contains an unsafe path segment")
        return "/".join(parts)

    def _object_key(self, storage_path: str) -> str:
        # Handles object key through the adapter boundary, letting services use one interface across local and
        # external backends.
        normalized = self._normalize_storage_path(storage_path)
        return f"{self.prefix}/{normalized}" if self.prefix else normalized

    def _cache_file(self, storage_path: str) -> Path:
        # Handles cache file through the adapter boundary, letting services use one interface across local and
        # external backends.
        normalized = self._normalize_storage_path(storage_path)
        path = (self.cache_path / normalized).resolve()
        try:
            path.relative_to(self.cache_path)
        except ValueError:
            raise ValueError("Resolved cache path is outside the configured cache root")
        return path

    def save_bytes(
        self,
        tenant_id: UUID,
        brand_space_id: UUID | None,
        category: str,
        filename: str,
        content: bytes,
    ) -> StoredObject:
        # Handles save bytes through the adapter boundary, letting services use one interface across local and
        # external backends.
        relative_path = self.build_relative_path(tenant_id, brand_space_id, category, filename)
        put_params: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": self._object_key(relative_path),
            "Body": content,
        }
        content_type = mimetypes.guess_type(filename)[0]
        if content_type:
            put_params["ContentType"] = content_type
        self.client.put_object(**put_params)
        cache_file = self._cache_file(relative_path)
        ensure_parent(cache_file)
        cache_file.write_bytes(content)
        return StoredObject(storage_path=relative_path, absolute_path=str(cache_file))

    def read_bytes(self, storage_path: str) -> bytes:
        # Handles read bytes through the adapter boundary, letting services use one interface across local and
        # external backends.
        response = self.client.get_object(Bucket=self.bucket, Key=self._object_key(storage_path))
        return response["Body"].read()

    def exists(self, storage_path: str) -> bool:
        # Handles exists through the adapter boundary, letting services use one interface across local and
        # external backends.
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._object_key(storage_path))
            return True
        except Exception:  # noqa: BLE001 - boto clients expose provider-specific exception classes
            return False

    def delete(self, storage_path: str) -> None:
        # Deletes the stored object through the adapter boundary, letting services use one interface across local and
        # external backends.
        self.client.delete_object(Bucket=self.bucket, Key=self._object_key(storage_path))
        with contextlib.suppress(ValueError, FileNotFoundError):
            self._cache_file(storage_path).unlink()

    def absolute_path(self, storage_path: str) -> str:
        # Handles absolute path through the adapter boundary, letting services use one interface across local
        # and external backends.
        cache_file = self._cache_file(storage_path)
        if not cache_file.exists():
            ensure_parent(cache_file)
            self.client.download_file(self.bucket, self._object_key(storage_path), str(cache_file))
        return str(cache_file)

    def presigned_url(
        self,
        storage_path: str,
        *,
        filename: str | None = None,
        download: bool = False,
        expires_in: int | None = None,
    ) -> str:
        # Handles presigned URL through the adapter boundary, letting services use one interface across local
        # and external backends.
        params: dict[str, Any] = {"Bucket": self.bucket, "Key": self._object_key(storage_path)}
        if filename:
            disposition = "attachment" if download else "inline"
            safe_filename = sanitize_filename(filename, fallback=Path(storage_path).name, max_length=128)
            params["ResponseContentDisposition"] = f'{disposition}; filename="{safe_filename}"'
        return self.client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires_in or self.settings.signed_asset_url_ttl_seconds,
        )


def get_object_storage() -> ObjectStorage:
    # Fetches object storage through the adapter boundary, letting services use one interface across local and
    # external backends.
    provider = str(get_settings().object_storage_provider or "local").strip().lower()
    if provider == "s3":
        return S3ObjectStorage()
    return LocalObjectStorage()
