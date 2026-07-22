# FastAPI route handlers live here; they validate request inputs, call services, and return response schemas.
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentPrincipal, assert_tenant_access, get_current_principal, require_roles
from app.core.enums import RoleCode
from app.db.session import get_db_session
from app.schemas.common import MessageResponse
from app.schemas.tenant import (
    ActivationEmailStatus,
    TenantBrandUsageTargetsResponse,
    TenantBrandUsageTargetsUpdate,
    TenantCreateRequest,
    TenantCreateResponse,
    TenantLogoUploadRequest,
    TenantBrandSpaceSummaryResponse,
    TenantResponse,
    TenantSummaryResponse,
    TenantUpdateRequest,
    TenantUsageLimitUpdate,
    TenantUsageSummary,
    TenantUserCreateRequest,
    TenantUserCreateResponse,
    TenantUserResponse,
    TenantUserUpdateRequest,
)
from app.services.tenant import TenantService


router = APIRouter()


@router.post("", response_model=TenantCreateResponse, dependencies=[Depends(require_roles(RoleCode.SUPER_ADMIN))])
async def create_tenant(
    payload: TenantCreateRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TenantCreateResponse:
    # Serves the tenant creation endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    tenant, delivery = await TenantService(session).create_tenant(payload)
    return TenantCreateResponse.model_validate(
        {
            **TenantResponse.model_validate(tenant).model_dump(),
            "activation_email": {
                "attempted": delivery.attempted,
                "delivered": delivery.delivered,
                "recipient_email": delivery.recipient_email,
                "reason": delivery.reason,
            },
        }
    )


@router.get("", response_model=list[TenantSummaryResponse], dependencies=[Depends(require_roles(RoleCode.SUPER_ADMIN))])
async def list_tenants(session: AsyncSession = Depends(get_db_session)) -> list[TenantSummaryResponse]:
    # Serves the tenants listing endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    service = TenantService(session)
    tenants = await service.list_tenants()
    summaries = [await service.get_tenant_summary(tenant.id) for tenant in tenants]
    return [TenantSummaryResponse.model_validate(item) for item in summaries]


@router.get("/{tenant_id}", response_model=TenantSummaryResponse)
async def get_tenant(
    tenant_id: UUID,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN, RoleCode.TENANT_USER)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> TenantSummaryResponse:
    # Serves the tenant detail lookup endpoint; it uses FastAPI dependencies, delegates work to services, and
    # returns the response schema.
    assert_tenant_access(principal, tenant_id)
    summary = await TenantService(session).get_tenant_summary(tenant_id)
    return TenantSummaryResponse.model_validate(summary)


@router.post("/{tenant_id}/logo", response_model=TenantSummaryResponse)
async def upload_tenant_logo(
    tenant_id: UUID,
    payload: TenantLogoUploadRequest,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> TenantSummaryResponse:
    # Serves the tenant logo upload endpoint; it uses FastAPI dependencies, delegates work to services, and
    # returns the response schema.
    assert_tenant_access(principal, tenant_id)
    service = TenantService(session)
    await service.upload_logo(tenant_id, payload)
    summary = await service.get_tenant_summary(tenant_id)
    return TenantSummaryResponse.model_validate(summary)


@router.put("/{tenant_id}", response_model=TenantSummaryResponse)
async def update_tenant(
    tenant_id: UUID,
    payload: TenantUpdateRequest,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> TenantSummaryResponse:
    # Serves the tenant update endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    assert_tenant_access(principal, tenant_id)
    service = TenantService(session)
    await service.update_tenant(tenant_id, payload, principal.role_codes)
    summary = await service.get_tenant_summary(tenant_id)
    return TenantSummaryResponse.model_validate(summary)


@router.put("/{tenant_id}/brand-usage-targets", response_model=TenantBrandUsageTargetsResponse)
async def update_brand_usage_targets(
    tenant_id: UUID,
    payload: TenantBrandUsageTargetsUpdate,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN, RoleCode.TENANT_USER)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> TenantBrandUsageTargetsResponse:
    # Serves the brand usage targets update endpoint; it uses FastAPI dependencies, delegates work to services,
    # and returns the response schema.
    assert_tenant_access(principal, tenant_id)
    targets = await TenantService(session).update_brand_usage_targets(tenant_id, payload.brand_usage_targets)
    return TenantBrandUsageTargetsResponse(brand_usage_targets=targets)


@router.delete(
    "/{tenant_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles(RoleCode.SUPER_ADMIN))],
)
async def delete_tenant(
    tenant_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    # Serves the tenant deletion endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    await TenantService(session).delete_tenant(tenant_id)
    return MessageResponse(message="Tenant deleted")


@router.get("/{tenant_id}/users", response_model=list[TenantUserResponse])
async def list_users(
    tenant_id: UUID,
    role_codes: str | None = Query(default=None),
    exclude_role_codes: str | None = Query(default=None),
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[TenantUserResponse]:
    # Serves the users listing endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    assert_tenant_access(principal, tenant_id)
    service = TenantService(session)
    requested_role_codes = (
        {role_code.strip() for role_code in role_codes.split(",") if role_code.strip()}
        if role_codes
        else None
    )
    requested_excluded_role_codes = (
        {role_code.strip() for role_code in exclude_role_codes.split(",") if role_code.strip()}
        if exclude_role_codes
        else None
    )
    users = await service.list_users(tenant_id, requested_role_codes, requested_excluded_role_codes)
    enriched = [await service.build_user_summary(user) for user in users]
    return [TenantUserResponse.model_validate(item) for item in enriched]


@router.get("/{tenant_id}/brand-spaces", response_model=list[TenantBrandSpaceSummaryResponse])
async def list_tenant_brand_spaces(
    tenant_id: UUID,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[TenantBrandSpaceSummaryResponse]:
    # Serves the tenant brand spaces listing endpoint; it uses FastAPI dependencies, delegates work to services,
    # and returns the response schema.
    assert_tenant_access(principal, tenant_id)
    service = TenantService(session)
    summaries = await service.list_tenant_brand_space_summaries(tenant_id)
    return [TenantBrandSpaceSummaryResponse.model_validate(item) for item in summaries]


@router.post("/{tenant_id}/users", response_model=TenantUserCreateResponse)
async def create_tenant_user(
    tenant_id: UUID,
    payload: TenantUserCreateRequest,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> TenantUserCreateResponse:
    # Serves the tenant user creation endpoint; it uses FastAPI dependencies, delegates work to services, and
    # returns the response schema.
    assert_tenant_access(principal, tenant_id)
    service = TenantService(session)
    user, delivery = await service.create_tenant_user(
        tenant_id,
        payload,
        created_by_admin_email=principal.email,
    )
    summary = await service.build_user_summary(user)
    return TenantUserCreateResponse.model_validate(
        {
            **summary,
            "activation_email": {
                "attempted": delivery.attempted,
                "delivered": delivery.delivered,
                "recipient_email": delivery.recipient_email,
                "reason": delivery.reason,
            },
        }
    )


@router.get("/{tenant_id}/users/{user_id}", response_model=TenantUserResponse)
async def get_user(
    tenant_id: UUID,
    user_id: UUID,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> TenantUserResponse:
    # Serves the user detail lookup endpoint; it uses FastAPI dependencies, delegates work to services, and
    # returns the response schema.
    assert_tenant_access(principal, tenant_id)
    summary = await TenantService(session).get_user_summary(tenant_id, user_id)
    return TenantUserResponse.model_validate(summary)


@router.put("/{tenant_id}/users/{user_id}", response_model=TenantUserResponse)
async def update_user(
    tenant_id: UUID,
    user_id: UUID,
    payload: TenantUserUpdateRequest,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> TenantUserResponse:
    # Serves the user update endpoint; it uses FastAPI dependencies, delegates work to services, and returns the
    # response schema.
    assert_tenant_access(principal, tenant_id)
    if (
        user_id == principal.user_id
        and payload.role_code is not None
        and payload.role_code not in principal.role_codes
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change your own admin role.",
        )
    service = TenantService(session)
    user = await service.update_tenant_user(
        tenant_id,
        user_id,
        payload,
        principal.user_id,
        principal.role_codes,
        principal.email,
    )
    return TenantUserResponse.model_validate(await service.build_user_summary(user))


@router.post("/{tenant_id}/users/{user_id}/deactivate", response_model=MessageResponse)
async def deactivate_user(
    tenant_id: UUID,
    user_id: UUID,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    # Serves the deactivate user endpoint; it uses FastAPI dependencies, delegates work to services, and returns
    # the response schema.
    assert_tenant_access(principal, tenant_id)
    await TenantService(session).deactivate_user(
        tenant_id,
        user_id,
        principal.user_id,
        principal.role_codes,
        principal.email,
    )
    return MessageResponse(message="User deactivated")


@router.post("/{tenant_id}/users/{user_id}/resend-activation", response_model=ActivationEmailStatus)
async def resend_activation_link(
    tenant_id: UUID,
    user_id: UUID,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ActivationEmailStatus:
    # Serves the resend activation endpoint; it delegates token refresh and email delivery to the tenant service.
    assert_tenant_access(principal, tenant_id)
    delivery = await TenantService(session).resend_activation_link(
        tenant_id,
        user_id,
        triggered_by_admin_email=principal.email,
    )
    return ActivationEmailStatus.model_validate(
        {
            "attempted": delivery.attempted,
            "delivered": delivery.delivered,
            "recipient_email": delivery.recipient_email,
            "reason": delivery.reason,
        }
    )


@router.put("/{tenant_id}/usage-limits", response_model=MessageResponse, dependencies=[Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN))])
async def update_usage_limits(
    tenant_id: UUID,
    payload: TenantUsageLimitUpdate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    # Serves the usage limits update endpoint; it uses FastAPI dependencies, delegates work to services, and
    # returns the response schema.
    assert_tenant_access(principal, tenant_id)
    await TenantService(session).update_usage_limits(tenant_id, payload)
    return MessageResponse(message="Usage limits updated")


@router.get("/{tenant_id}/usage-summary", response_model=TenantUsageSummary)
async def get_usage_summary(
    tenant_id: UUID,
    _: CurrentPrincipal = Depends(require_roles(RoleCode.SUPER_ADMIN, RoleCode.TENANT_ADMIN)),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> TenantUsageSummary:
    # Serves the usage summary detail lookup endpoint; it uses FastAPI dependencies, delegates work to services,
    # and returns the response schema.
    assert_tenant_access(principal, tenant_id)
    summary = await TenantService(session).get_usage_summary(tenant_id)
    return TenantUsageSummary.model_validate(summary)
