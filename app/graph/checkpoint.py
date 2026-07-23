from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Persist Phase-1 checkpoints to disk so uvicorn --reload does not wipe approve state.
_TTL_SECONDS = 60 * 60 * 6  # 6 hours
_CHECKPOINT_DIR = Path(__file__).resolve().parents[2] / "storage" / "pipeline_checkpoints"


def _ensure_dir() -> Path:
    _CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return _CHECKPOINT_DIR


def _path_for(run_id: str) -> Path:
    safe = "".join(ch for ch in str(run_id) if ch.isalnum() or ch in "-_")
    return _ensure_dir() / f"{safe}.json"


def _purge_expired() -> None:
    now = time.time()
    root = _ensure_dir()
    for path in root.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            created = float(data.get("created_at") or 0)
            if now - created > _TTL_SECONDS:
                path.unlink(missing_ok=True)
                logger.info("pipeline_checkpoint.purged", run_id=path.stem)
        except Exception:
            continue


def save_checkpoint(run_id: str, state: dict[str, Any], status: str = "awaiting_blueprint_approval") -> None:
    _purge_expired()
    payload = {
        "state": deepcopy(state),
        "created_at": time.time(),
        "status": status,
    }
    path = _path_for(run_id)
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")
    logger.info("pipeline_checkpoint.saved", run_id=run_id, status=status, path=str(path))


def get_checkpoint(run_id: str) -> dict[str, Any] | None:
    _purge_expired()
    path = _path_for(run_id)
    if not path.exists():
        logger.warning("pipeline_checkpoint.miss", run_id=run_id)
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return deepcopy(data.get("state") or {})
    except Exception as exc:
        logger.error("pipeline_checkpoint.read_failed", run_id=run_id, error=str(exc))
        return None


def get_checkpoint_status(run_id: str) -> str | None:
    _purge_expired()
    path = _path_for(run_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("status")
    except Exception:
        return None


def update_checkpoint_status(run_id: str, status: str) -> None:
    path = _path_for(run_id)
    if not path.exists():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = status
        path.write_text(json.dumps(data, default=str), encoding="utf-8")
    except Exception as exc:
        logger.warning("pipeline_checkpoint.status_update_failed", run_id=run_id, error=str(exc))


def delete_checkpoint(run_id: str) -> None:
    path = _path_for(run_id)
    path.unlink(missing_ok=True)
    logger.info("pipeline_checkpoint.deleted", run_id=run_id)


def serialize_state_for_checkpoint(state: dict[str, Any]) -> dict[str, Any]:
    """Convert ViolytState (may contain Pydantic models) to JSON-friendly dict."""

    def _dump(obj: Any) -> Any:
        if obj is None:
            return None
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if isinstance(obj, dict):
            return {k: _dump(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_dump(v) for v in obj]
        return obj

    return _dump(state)
