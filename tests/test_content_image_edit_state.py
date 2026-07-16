from uuid import uuid4

from app.api.routes import content as content_routes
from app.schemas.common import AssetReference
from app.schemas.content import ContentImageEditStateRequest


class _TokenDeliveryStub:
    counter = 0

    def build_signed_url(self, *, storage_path, filename=None, download=False, expires_in=None):
        type(self).counter += 1
        return f"https://assets.local/download?token=fresh-{type(self).counter}"


def _asset(asset_id):
    return AssetReference(
        asset_id=asset_id,
        mime_type="image/png",
        storage_path="tenant/brand/generated/image.png",
        asset_url="https://assets.local/download?token=expired",
        width=1080,
        height=1080,
        asset_role="preview",
    )


def test_image_edit_state_refreshes_cached_variant_asset_urls(monkeypatch) -> None:
    monkeypatch.setattr(content_routes, "AssetDeliveryService", _TokenDeliveryStub)
    content_routes._IMAGE_EDIT_STATES.clear()
    _TokenDeliveryStub.counter = 0

    content_version_id = uuid4()
    asset_id = uuid4()
    first_state = content_routes._image_edit_state(
        ContentImageEditStateRequest(
            content_version_id=content_version_id,
            source_asset=_asset(asset_id),
        )
    )
    second_state = content_routes._image_edit_state(
        ContentImageEditStateRequest(
            content_version_id=content_version_id,
            source_asset=_asset(asset_id),
        )
    )

    assert first_state.variants[0].asset.asset_url.endswith("fresh-1")
    assert second_state.variants[0].asset.asset_url.endswith("fresh-2")
    assert "expired" not in second_state.variants[0].asset.asset_url
