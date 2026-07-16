from uuid import uuid4

from app.api.routes.review import _review_display_assets
from app.models.content import ContentVersion, GeneratedAsset
from app.schemas.common import AssetReference


class _DeliveryStub:
    def build_signed_url(self, *, storage_path, filename=None, download=False, expires_in=None):
        return f"https://assets.local/download?token={filename or storage_path}"


def _content(slide_count: int) -> ContentVersion:
    return ContentVersion(
        id=uuid4(),
        tenant_id=uuid4(),
        brand_space_id=uuid4(),
        session_id=uuid4(),
        created_by=uuid4(),
        title="Carousel",
        prompt="Create carousel",
        generated_payload={
            "metadata": {
                "carousel_slide_specs": [
                    {"slide_index": index}
                    for index in range(1, slide_count + 1)
                ]
            }
        },
        blueprint_payload={},
        explainability_metadata={},
        studio_panel={"format": "carousel"},
    )


def _generated_asset(content: ContentVersion, slide_index: int, role: str) -> GeneratedAsset:
    return GeneratedAsset(
        id=uuid4(),
        tenant_id=content.tenant_id,
        brand_space_id=content.brand_space_id,
        content_version_id=content.id,
        asset_role=role,
        mime_type="image/png",
        storage_path=f"tenant/brand/carousel-slide-{slide_index}.png",
        width=1080,
        height=1080,
        metadata_json={
            "render_source": "ai",
            "generation_stage": "final_render",
            "slide_index": slide_index,
            "slide_count": 3,
        },
    )


def _payload_asset(content: ContentVersion, asset: GeneratedAsset) -> AssetReference:
    return AssetReference(
        asset_id=asset.id,
        mime_type=asset.mime_type,
        storage_path=asset.storage_path,
        asset_url="https://assets.local/download?token=payload-single",
        width=asset.width,
        height=asset.height,
        asset_role=asset.asset_role,
    )


def test_review_display_assets_uses_complete_carousel_db_assets_when_payload_is_partial() -> None:
    content = _content(3)
    assets = [
        _generated_asset(content, 1, "render_preview"),
        _generated_asset(content, 2, "render_export"),
        _generated_asset(content, 3, "render_export"),
    ]

    display_assets = _review_display_assets(
        content,
        assets,
        [_payload_asset(content, assets[0])],
        _DeliveryStub(),
    )

    assert [asset.storage_path for asset in display_assets] == [
        "tenant/brand/carousel-slide-1.png",
        "tenant/brand/carousel-slide-2.png",
        "tenant/brand/carousel-slide-3.png",
    ]
    assert all("payload-single" not in (asset.asset_url or "") for asset in display_assets)


def test_review_display_assets_keeps_static_payload_asset() -> None:
    content = _content(1)
    asset = _generated_asset(content, 1, "render_preview")
    payload_asset = _payload_asset(content, asset)

    display_assets = _review_display_assets(content, [asset], [payload_asset], _DeliveryStub())

    assert display_assets == [payload_asset]
