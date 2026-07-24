import pytest
from pydantic import ValidationError

from app.schemas.tenant import TenantCreateRequest, TenantUpdateRequest, TenantUsageLimitUpdate


@pytest.mark.parametrize("field_name", ["contact_number", "admin_phone_number"])
@pytest.mark.parametrize("invalid_value", ["123456789", "12345678901", "12345abcde", "+919876543210"])
def test_tenant_update_rejects_non_ten_digit_phone_values(field_name: str, invalid_value: str) -> None:
    with pytest.raises(ValidationError):
        TenantUpdateRequest.model_validate({field_name: invalid_value})


def test_tenant_update_accepts_ten_digit_phone_values() -> None:
    payload = TenantUpdateRequest(
        contact_number="9876543210",
        admin_phone_number="9123456780",
    )

    assert payload.contact_number == "9876543210"
    assert payload.admin_phone_number == "9123456780"


def test_tenant_create_accepts_ten_digit_phone_values() -> None:
    payload = TenantCreateRequest(
        name="Acme",
        slug="acme",
        contact_email="tenant@example.com",
        contact_number="9876543210",
        admin_full_name="Admin User",
        admin_email="admin@example.com",
        admin_phone_number="9123456780",
        usage_limits=TenantUsageLimitUpdate(
            max_users=1,
            max_brand_spaces=1,
            max_content_generations=1,
            max_image_generations=1,
            max_ocr_pages=1,
        ),
    )

    assert payload.contact_number == "9876543210"
    assert payload.admin_phone_number == "9123456780"