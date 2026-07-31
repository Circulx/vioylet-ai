from __future__ import annotations

from collections.abc import Mapping
from typing import Any


LEGACY_NOTIFICATIONS_KEY = "notifications_enabled"
EMAIL_NOTIFICATIONS_KEY = "email_notifications_enabled"
IN_APP_NOTIFICATIONS_KEY = "in_app_notifications_enabled"


def notification_preference_enabled(metadata: Mapping[str, Any] | None, key: str) -> bool:
    preferences = metadata or {}
    value = preferences.get(key)
    if isinstance(value, bool):
        return value
    return preferences.get(LEGACY_NOTIFICATIONS_KEY, True) is not False


def email_notifications_enabled(metadata: Mapping[str, Any] | None) -> bool:
    return notification_preference_enabled(metadata, EMAIL_NOTIFICATIONS_KEY)


def in_app_notifications_enabled(metadata: Mapping[str, Any] | None) -> bool:
    return notification_preference_enabled(metadata, IN_APP_NOTIFICATIONS_KEY)
