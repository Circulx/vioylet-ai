# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from threading import Lock
from uuid import UUID


class ChatCancellationRegistry:
    # Business layer for chat cancellation registry; routes and workers pass validated inputs here and receive
    # domain results back.
    def __init__(self) -> None:
        # Wires the repositories and helper services this workflow reuses across its public methods.
        self._lock = Lock()
        self._cancelled: set[tuple[UUID, UUID, UUID]] = set()

    def request_cancel(self, tenant_id: UUID, brand_space_id: UUID, session_id: UUID) -> None:
        # Runs the request cancel service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        with self._lock:
            self._cancelled.add((tenant_id, brand_space_id, session_id))

    def clear(self, tenant_id: UUID, brand_space_id: UUID, session_id: UUID) -> None:
        # Runs the clear service flow by coordinating repositories, validators, and integrations, then returns
        # domain data.
        with self._lock:
            self._cancelled.discard((tenant_id, brand_space_id, session_id))

    def is_cancelled(self, tenant_id: UUID, brand_space_id: UUID, session_id: UUID) -> bool:
        # Runs the is cancelled service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        with self._lock:
            return (tenant_id, brand_space_id, session_id) in self._cancelled


chat_cancellation_registry = ChatCancellationRegistry()
