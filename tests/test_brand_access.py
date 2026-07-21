from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.dependencies import CurrentPrincipal, assert_brand_access, assert_brand_manage_access
from app.core.enums import RoleCode


def _principal(role_codes: set[str], *, brand_space_ids: set | None = None) -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        email="user@example.com",
        role_codes=role_codes,
        brand_space_ids=brand_space_ids or set(),
    )


def test_brand_access_keeps_brand_user_limited_to_assigned_brands() -> None:
    assigned_brand_id = uuid4()
    principal = _principal({RoleCode.BRAND_USER.value}, brand_space_ids={assigned_brand_id})

    assert_brand_access(principal, assigned_brand_id)

    with pytest.raises(HTTPException) as exc:
        assert_brand_access(principal, uuid4())

    assert exc.value.status_code == 403


def test_brand_access_rejects_unassigned_brand_user_with_empty_memberships() -> None:
    principal = _principal({RoleCode.BRAND_USER.value})

    with pytest.raises(HTTPException) as exc:
        assert_brand_access(principal, uuid4())

    assert exc.value.status_code == 403


def test_brand_manage_access_is_tenant_admin_only() -> None:
    assert_brand_manage_access(_principal({RoleCode.TENANT_ADMIN.value}))

    for role_code in (RoleCode.TENANT_USER.value, RoleCode.BRAND_USER.value):
        with pytest.raises(HTTPException) as exc:
            assert_brand_manage_access(_principal({role_code}))

        assert exc.value.status_code == 403
