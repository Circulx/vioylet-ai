from threading import Lock
from uuid import UUID


class ChatCancellationRegistry:
    def __init__(self) -> None:
        self._lock = Lock()
        self._cancelled: set[tuple[UUID, UUID, UUID]] = set()

    def request_cancel(self, tenant_id: UUID, brand_space_id: UUID, session_id: UUID) -> None:
        with self._lock:
            self._cancelled.add((tenant_id, brand_space_id, session_id))

    def clear(self, tenant_id: UUID, brand_space_id: UUID, session_id: UUID) -> None:
        with self._lock:
            self._cancelled.discard((tenant_id, brand_space_id, session_id))

    def is_cancelled(self, tenant_id: UUID, brand_space_id: UUID, session_id: UUID) -> bool:
        with self._lock:
            return (tenant_id, brand_space_id, session_id) in self._cancelled


chat_cancellation_registry = ChatCancellationRegistry()
