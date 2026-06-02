from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.integrations.object_storage import LocalObjectStorage, S3ObjectStorage, get_object_storage


def _workspace_test_dir(label: str) -> Path:
    path = Path("storage") / "_test_artifacts" / "object_storage" / f"{label}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


class _FakeBody:
    def __init__(self, value: bytes) -> None:
        self.value = value

    def read(self) -> bytes:
        return self.value


class _FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}
        self.content_types: dict[tuple[str, str], str] = {}
        self.downloads: list[tuple[str, str, str]] = []

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, **kwargs: object) -> None:  # noqa: N803
        self.objects[(Bucket, Key)] = Body
        if kwargs.get("ContentType"):
            self.content_types[(Bucket, Key)] = str(kwargs["ContentType"])

    def get_object(self, *, Bucket: str, Key: str):  # noqa: N803, ANN201
        return {"Body": _FakeBody(self.objects[(Bucket, Key)])}

    def head_object(self, *, Bucket: str, Key: str) -> None:  # noqa: N803
        if (Bucket, Key) not in self.objects:
            raise RuntimeError("missing")

    def delete_object(self, *, Bucket: str, Key: str) -> None:  # noqa: N803
        self.objects.pop((Bucket, Key), None)

    def download_file(self, Bucket: str, Key: str, Filename: str) -> None:  # noqa: N803
        Path(Filename).parent.mkdir(parents=True, exist_ok=True)
        Path(Filename).write_bytes(self.objects[(Bucket, Key)])
        self.downloads.append((Bucket, Key, Filename))

    def generate_presigned_url(self, operation: str, *, Params: dict, ExpiresIn: int) -> str:  # noqa: N803
        return f"https://signed.example/{operation}/{Params['Bucket']}/{Params['Key']}?ttl={ExpiresIn}"


def test_get_object_storage_defaults_to_local(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "object_storage_provider", "local")
    monkeypatch.setattr(settings, "object_storage_base_path", str(_workspace_test_dir("local")))

    storage = get_object_storage()
    assert isinstance(storage, LocalObjectStorage)

    stored = storage.save_bytes(uuid4(), uuid4(), "uploads", "logo.png", b"logo")
    assert storage.exists(stored.storage_path)
    assert storage.read_bytes(stored.storage_path) == b"logo"
    assert Path(storage.absolute_path(stored.storage_path)).exists()


def test_s3_object_storage_uses_relative_keys_and_local_cache(monkeypatch) -> None:
    settings = get_settings()
    fake_client = _FakeS3Client()
    fake_boto3 = SimpleNamespace(client=lambda service, **kwargs: fake_client)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setattr(settings, "object_storage_provider", "s3")
    monkeypatch.setattr(settings, "aws_s3_bucket", "violyt-test")
    monkeypatch.setattr(settings, "aws_s3_prefix", "staging")
    monkeypatch.setattr(settings, "aws_region", "ap-south-1")
    monkeypatch.setattr(settings, "object_storage_cache_path", str(_workspace_test_dir("s3-cache")))
    monkeypatch.setattr(settings, "signed_asset_url_ttl_seconds", 123)

    storage = get_object_storage()
    assert isinstance(storage, S3ObjectStorage)

    stored = storage.save_bytes(uuid4(), uuid4(), "generated/reference-conditioning", "slide 1.png", b"image")
    object_key = f"staging/{stored.storage_path}"
    assert ("violyt-test", object_key) in fake_client.objects
    assert fake_client.content_types[("violyt-test", object_key)] == "image/png"
    assert Path(stored.absolute_path).read_bytes() == b"image"
    assert storage.exists(stored.storage_path)
    assert storage.read_bytes(stored.storage_path) == b"image"

    Path(stored.absolute_path).unlink()
    cached_path = storage.absolute_path(stored.storage_path)
    assert Path(cached_path).read_bytes() == b"image"
    assert fake_client.downloads[-1][1] == object_key

    url = storage.presigned_url(stored.storage_path, filename="slide.png")
    assert "https://signed.example/get_object/violyt-test/staging/" in url
    assert "ttl=123" in url

    storage.delete(stored.storage_path)
    assert not storage.exists(stored.storage_path)
    assert not Path(cached_path).exists()


def test_local_object_storage_rejects_path_traversal(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "object_storage_base_path", str(_workspace_test_dir("local-secure")))

    storage = LocalObjectStorage()

    with pytest.raises(ValueError):
        storage.absolute_path("../outside.png")


def test_s3_object_storage_rejects_path_traversal(monkeypatch) -> None:
    settings = get_settings()
    fake_client = _FakeS3Client()
    fake_boto3 = SimpleNamespace(client=lambda service, **kwargs: fake_client)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setattr(settings, "aws_s3_bucket", "violyt-test")
    monkeypatch.setattr(settings, "object_storage_cache_path", str(_workspace_test_dir("s3-secure")))

    storage = S3ObjectStorage()

    with pytest.raises(ValueError):
        storage.presigned_url("../outside.png")
