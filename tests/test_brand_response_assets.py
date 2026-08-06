from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from app.api.routes import brand as brand_route
from app.schemas.brand import BrandResponse


class BrandResponseAssetTests(TestCase):
    def test_brand_response_refreshes_persisted_logo_urls(self) -> None:
        def build_signed_url(
            _service,
            *,
            storage_path: str,
            filename: str | None = None,
            download: bool = False,
            expires_in: int | None = None,
        ) -> str:
            del filename, download, expires_in
            return f"https://assets.example.test/download?path={storage_path}"

        now = datetime.now(timezone.utc)
        brand = BrandResponse(
            id=uuid4(),
            tenant_id=uuid4(),
            name="Example",
            slug="example",
            description="Example brand",
            lifecycle_state="active",
            is_finalized=True,
            resolved_brand_context={
                "identity": {
                    "logo_asset_path": "tenant/brand/logo/primary.png",
                    "logo_asset_url": "https://assets.example.test/download?token=expired",
                    "logo_assets": [
                        {
                            "storage_path": "tenant/brand/logo/primary.png",
                            "asset_url": "https://assets.example.test/download?token=expired",
                        }
                    ],
                }
            },
            created_at=now,
            updated_at=now,
        )

        with patch.object(
            brand_route.AssetDeliveryService,
            "build_signed_url",
            autospec=True,
            side_effect=build_signed_url,
        ):
            response = brand_route._brand_response(brand)

        identity = response.resolved_brand_context["identity"]
        expected_url = "https://assets.example.test/download?path=tenant/brand/logo/primary.png"

        self.assertEqual(identity["logo_asset_url"], expected_url)
        self.assertEqual(identity["logo_assets"][0]["asset_url"], expected_url)
        self.assertEqual(identity["logo_assets"][0]["url"], expected_url)
