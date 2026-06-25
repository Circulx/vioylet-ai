from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CurrentPrincipal, assert_brand_access, get_brand_scope_header, get_current_principal, require_brand_scope
from app.db.session import get_db_session
from app.core.exceptions import ChatGenerationCancelledError
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatSendResponse,
    ChatSessionCreateRequest,
    ChatSessionResponse,
    ChatSessionUpdateRequest,
)
from app.services.chat import ChatService


router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    payload: ChatSessionCreateRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionResponse:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    chat_session = await ChatService(session).create_session(principal.tenant_id, brand_scope, principal.user_id, payload)
    return ChatSessionResponse.model_validate(chat_session)


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_chat_sessions(
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatSessionResponse]:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    items = await ChatService(session).list_sessions(principal.tenant_id, brand_scope)
    return [ChatSessionResponse.model_validate(item) for item in items]


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_chat_session(
    session_id: UUID,
    payload: ChatSessionUpdateRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSessionResponse:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    chat_session = await ChatService(session).update_session(
        session_id=session_id,
        tenant_id=principal.tenant_id,
        brand_space_id=brand_scope,
        payload=payload,
    )
    return ChatSessionResponse.model_validate(chat_session)


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: UUID,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    return await ChatService(session).delete_session(
        session_id=session_id,
        tenant_id=principal.tenant_id,
        brand_space_id=brand_scope,
    )


@router.post("/sessions/{session_id}/cancel")
async def cancel_chat_generation(
    session_id: UUID,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    return await ChatService(session).cancel_generation(
        session_id=session_id,
        tenant_id=principal.tenant_id,
        brand_space_id=brand_scope,
    )


@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def list_chat_messages(
    session_id: UUID,
    limit: int = Query(default=150, ge=1, le=150),
    before_created_at: datetime | None = Query(default=None),
    before_id: UUID | None = Query(default=None),
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> list[ChatMessageResponse]:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    chat_service = ChatService(session)
    await chat_service.get_session(session_id, tenant_id=principal.tenant_id, brand_space_id=brand_scope)
    items = await chat_service.list_messages(
        session_id,
        limit=limit,
        before_created_at=before_created_at,
        before_id=before_id,
    )
    return [ChatMessageResponse.model_validate(item) for item in items]


@router.post("/sessions/{session_id}/messages", response_model=ChatSendResponse)
async def send_chat_message(
    session_id: UUID,
    payload: ChatMessageCreateRequest,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> ChatSendResponse:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    try:
        user_message, assistant_message = await ChatService(session).send_message(
            tenant_id=principal.tenant_id,
            brand_space_id=brand_scope,
            user_id=principal.user_id,
            session_id=session_id,
            payload=payload,
        )
    except ChatGenerationCancelledError as exc:
        await session.rollback()
        raise HTTPException(status_code=499, detail=str(exc)) from exc
    return ChatSendResponse(
        user_message=ChatMessageResponse.model_validate(user_message),
        assistant_message=ChatMessageResponse.model_validate(assistant_message),
    )


@router.delete("/messages/{message_id}")
async def delete_chat_message(
    message_id: UUID,
    brand_scope: UUID = Depends(get_brand_scope_header),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    brand_scope = require_brand_scope(brand_scope)
    assert_brand_access(principal, brand_scope)
    return await ChatService(session).delete_message(
        message_id=message_id,
        tenant_id=principal.tenant_id,
        brand_space_id=brand_scope,
    )
