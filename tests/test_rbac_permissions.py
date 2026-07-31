from app.core.enums import RoleCode
from app.services.bootstrap import ROLE_PERMISSION_MAP


def test_super_user_role_is_brand_space_view_only() -> None:
    assert "brand.manage" not in ROLE_PERMISSION_MAP[RoleCode.TENANT_USER]
