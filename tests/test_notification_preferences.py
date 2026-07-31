import pytest

from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.services.notification import InAppNotificationService
from app.services.notification_preferences import email_notifications_enabled, in_app_notifications_enabled


def test_notification_preferences_default_to_enabled():
    assert email_notifications_enabled(None) is True
    assert in_app_notifications_enabled(None) is True


def test_legacy_notification_preference_is_used_as_fallback():
    metadata = {"notifications_enabled": False}

    assert email_notifications_enabled(metadata) is False
    assert in_app_notifications_enabled(metadata) is False


def test_channel_preferences_override_legacy_preference_independently():
    metadata = {
        "notifications_enabled": False,
        "email_notifications_enabled": True,
        "in_app_notifications_enabled": False,
    }

    assert email_notifications_enabled(metadata) is True
    assert in_app_notifications_enabled(metadata) is False


def test_email_can_be_disabled_without_disabling_in_app_notifications():
    metadata = {
        "email_notifications_enabled": False,
        "in_app_notifications_enabled": True,
    }

    assert email_notifications_enabled(metadata) is False
    assert in_app_notifications_enabled(metadata) is True

@pytest.mark.asyncio
async def test_in_app_service_uses_the_in_app_preference():
    session = SimpleNamespace(
        get=AsyncMock(
            return_value=SimpleNamespace(
                is_active=True,
                metadata_json={"in_app_notifications_enabled": False},
            )
        )
    )
    service = InAppNotificationService(session)

    assert await service._notifications_enabled_for_user(SimpleNamespace()) is False
