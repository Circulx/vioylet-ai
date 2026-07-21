from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.chat import assert_chat_brand_access
from app.core.dependencies import CurrentPrincipal
from app.core.enums import RoleCode


def _principal(role_codes: set[tr], *, brand_space_ids: set | None = None, tenant_id=None) -> CurrentPrincipal:
    return CurrentPrincipal(s
        user_id=uuid4(),
        tenant_id=tenant_id or uuid4(),
        email="user@example.com",
        role_codes=role_codes,
        brand_space_ids=brand_space_ids or set(),
    )


def test_chat_brand_access_allows_super_user_with_other_brand_memberships() -> None:
    brand_scope = uuid4()
    principal = _principal({RoleCode.TENANT_USER}, brand_space_ids={uuid4()})

    assert_chat_brand_access(principal, brand_scope)


def test_chat_brand_access_keeps_brand_user_limited_to_assigned_brands() -> None:
    principal = _principal({RoleCode.BRAND_USER}, brand_space_ids={uuid4()})

    with pytest.raises(HTTPException) as exc:
        assert_chat_brand_access(principal, uuid4())

    assert exc.value.status_code == 403


def test_chat_brand_access_keeps_platform_super_admin_blocked() -> None:
    principal = _principal({RoleCode.SUPER_ADMIN}, tenant_id=None)

    with pytest.raises(HTTPException) as exc:
        assert_chat_brand_access(principal, uuid4())

    assert exc.value.status_code == 403
