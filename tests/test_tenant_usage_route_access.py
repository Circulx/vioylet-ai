from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.api.routes.tenant import router
from app.core.dependencies import CurrentPrincipal
from app.core.enums import RoleCode


def _principal(role_code: RoleCode) -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        email="user@example.com",
        role_codes={role_code},
    )


def _usage_summary_role_checker():
    route = next(
        route
        for route in router.routes
        if isinstance(route, APIRoute) and route.name == "get_usage_summary"
    )
    return next(
        dependency.call
        for dependency in route.dependant.dependencies
        if dependency.name == "_"
    )


@pytest.mark.parametrize("role_code", [RoleCode.TENANT_ADMIN, RoleCode.TENANT_USER])
async def test_usage_summary_allows_tenant_dashboard_roles(role_code: RoleCode) -> None:
    principal = _principal(role_code)

    assert await _usage_summary_role_checker()(principal) is principal


async def test_usage_summary_keeps_brand_user_forbidden() -> None:
    with pytest.raises(HTTPException) as exc:
        await _usage_summary_role_checker()(_principal(RoleCode.BRAND_USER))

    assert exc.value.status_code == 403
