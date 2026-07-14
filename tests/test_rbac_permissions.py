from app.core.enums import RoleCode
from app.services.bootstrap import ROLE_PERMISSION_MAP


def test_super_user_role_keeps_brand_space_management_permission() -> None:
    assert "brand.manage" in ROLE_PERMISSION_MAP[RoleCode.TENANT_USER]
