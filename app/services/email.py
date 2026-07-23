# Service classes hold business workflows between the HTTP layer, repositories, and integrations.
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
import logging
import smtplib
import ssl
from urllib.parse import quote

from app.core.config import get_settings


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EmailDeliveryResult:
    # Business layer for email delivery result; routes and workers pass validated inputs here and receive domain
    # results back.
    attempted: bool
    delivered: bool
    recipient_email: str
    reason: str | None = None


class EmailService:
    # Business layer for email; routes and workers pass validated inputs here and receive domain results back.
    def __init__(self) -> None:
        # Wires the repositories and helper services this workflow reuses across its public methods.
        self.settings = get_settings()

    def is_configured(self) -> bool:
        # Runs the is configured service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        return bool(self.settings.smtp_host and self.settings.smtp_username and self.settings.smtp_password)

    def build_activation_link(self, token: str) -> str:
        # Runs the activation link service flow by coordinating repositories, validators, and integrations, then
        # returns domain data.
        base_url = self.settings.frontend_base_url.rstrip("/")
        return f"{base_url}/auth/activate?token={quote(token, safe='')}"

    def build_review_link(self, token: str) -> str:
        # Builds the public review thread URL used in comment notification emails.
        base_url = self.settings.frontend_base_url.rstrip("/")
        return f"{base_url}/review/{quote(token, safe='')}"

    def send_activation_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        token: str,
    ) -> EmailDeliveryResult:
        # Runs the send activation email service flow by coordinating repositories, validators, and
        # integrations, then returns domain data.
        activation_link = self.build_activation_link(token)
        subject = "Activate your Violyt account"
        greeting_name = recipient_name or recipient_email
        text_body = (
            f"Hello {greeting_name},\n\n"
            "Your Violyt account is ready. Use the link below to activate your account and create a password:\n\n"
            f"{activation_link}\n\n"
            "This link will expire automatically. If you did not expect this invitation, you can ignore this email."
        )
        html_body = (
            f"<p>Hello {greeting_name},</p>"
            "<p>Your Violyt account is ready. Use the button below to activate your account and create a password.</p>"
            f'<p><a href="{activation_link}" style="display:inline-block;padding:12px 20px;'
            'background:#3C2F8F;color:#ffffff;text-decoration:none;border-radius:8px;">Activate Account</a></p>'
            f"<p>If the button does not work, open this link:</p><p>{activation_link}</p>"
            "<p>This link will expire automatically. If you did not expect this invitation, you can ignore this email.</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_user_created_notification_email(
        self,
        admin_email: str,
        new_user_name: str,
        new_user_email: str,
        role_label: str,
        activation_delivery: EmailDeliveryResult,
        activation_sent_at: datetime,
        activation_expires_at: datetime,
        activation_attempts_done: int,
    ) -> EmailDeliveryResult:
        # Sends a non-sensitive creation notice to the tenant admin without exposing the user's activation link.
        subject = f"Activation email sent to {new_user_name}"
        escaped_user_name = escape(new_user_name)
        escaped_user_email = escape(new_user_email)
        escaped_role_label = escape(role_label)
        sent_at_utc = activation_sent_at.astimezone(timezone.utc)
        expires_at_utc = activation_expires_at.astimezone(timezone.utc)
        sent_label = sent_at_utc.strftime("%d/%m/%Y %H:%M UTC")
        expires_label = expires_at_utc.strftime("%d/%m/%Y %H:%M UTC")
        delivery_status = (
            "The activation email was sent successfully."
            if activation_delivery.delivered
            else f"The activation email was not sent: {activation_delivery.reason or 'Email delivery could not be completed.'}"
        )
        escaped_delivery_status = escape(delivery_status)
        text_body = (
            "Activation email notification\n\n"
            f"The activation email for the following {role_label} was sent to the user.\n\n"
            f"User name: {new_user_name}\n"
            f"User email: {new_user_email}\n"
            f"Activation email sent at: {sent_label}\n"
            f"Activation link valid until: {expires_label}\n"
            f"Total activation email attempts done: {activation_attempts_done}\n"
            f"{delivery_status}\n\n"
            "This admin notification is informational only. The activation link and activation button were sent only to the user."
        )
        html_body = (
            "<p><strong>Activation email notification</strong></p>"
            f"<p>The activation email for the following {escaped_role_label} was sent to the user.</p>"
            "<ul>"
            f"<li><strong>User name:</strong> {escaped_user_name}</li>"
            f"<li><strong>User email:</strong> {escaped_user_email}</li>"
            f"<li><strong>Activation email sent at:</strong> {escape(sent_label)}</li>"
            f"<li><strong>Activation link valid until:</strong> {escape(expires_label)}</li>"
            f"<li><strong>Total activation email attempts done:</strong> {activation_attempts_done}</li>"
            f"<li>{escaped_delivery_status}</li>"
            "</ul>"
            "<p>This admin notification is informational only. The activation link and activation button were sent only to the user.</p>"
        )
        return self._send_email(admin_email, subject, text_body, html_body)

    def send_password_reset_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        token: str,
    ) -> EmailDeliveryResult:
        # Runs the send password reset email service flow by coordinating repositories, validators, and
        # integrations, then returns domain data.
        reset_link = self.build_activation_link(token)
        subject = "Reset your Violyt password"
        greeting_name = recipient_name or recipient_email
        text_body = (
            f"Hello {greeting_name},\n\n"
            "We received a request to reset your Violyt password. Use the link below to continue:\n\n"
            f"{reset_link}\n\n"
            "If you did not request a password reset, you can ignore this email."
        )
        html_body = (
            f"<p>Hello {greeting_name},</p>"
            "<p>We received a request to reset your Violyt password. Use the button below to continue.</p>"
            f'<p><a href="{reset_link}" style="display:inline-block;padding:12px 20px;'
            'background:#3C2F8F;color:#ffffff;text-decoration:none;border-radius:8px;">Reset Password</a></p>'
            f"<p>If the button does not work, open this link:</p><p>{reset_link}</p>"
            "<p>If you did not request a password reset, you can ignore this email.</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_password_changed_confirmation_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
    ) -> EmailDeliveryResult:
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        subject = "Your Violyt Password Has Been Changed"
        text_body = (
            f"Hello {greeting_name},\n\n"
            "This is a confirmation that the password for your Violyt account has been changed successfully.\n\n"
            "If you made this change, no further action is required.\n\n"
            "If you did not change your password, please contact your administrator immediately and "
            "secure your account as soon as possible.\n\n"
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            "<p>This is a confirmation that the password for your Violyt account has been changed successfully.</p>"
            "<p>If you made this change, no further action is required.</p>"
            "<p>If you did not change your password, please contact your administrator immediately and "
            "secure your account as soon as possible.</p>"
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_two_factor_security_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        *,
        enabled: bool,
    ) -> EmailDeliveryResult:
        # Sends an account-security notice after a confirmed 2FA status change.
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        if enabled:
            subject = "Two-Factor Authentication Enabled"
            status_sentence = "Two-factor authentication has been successfully enabled for your Violyt account."
            protection_sentence = "Your account now has an additional layer of security."
            unexpected_sentence = (
                "If you did not enable two-factor authentication, please contact your administrator "
                "or support team immediately."
            )
        else:
            subject = "Two-Factor Authentication Disabled"
            status_sentence = "Two-factor authentication has been disabled for your Violyt account."
            protection_sentence = "Your account is no longer protected by two-factor authentication."
            unexpected_sentence = (
                "If you did not disable two-factor authentication, please contact your administrator "
                "or support team immediately."
            )

        text_body = (
            f"Hello {greeting_name},\n\n"
            f"{status_sentence}\n\n"
            f"{protection_sentence}\n\n"
            "If you performed this action, no further action is required.\n\n"
            f"{unexpected_sentence}\n\n"
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f"<p>{escape(status_sentence)}</p>"
            f"<p>{escape(protection_sentence)}</p>"
            "<p>If you performed this action, no further action is required.</p>"
            f"<p>{escape(unexpected_sentence)}</p>"
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_account_deactivated_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        *,
        deactivated_by_platform_owner: bool = False,
    ) -> EmailDeliveryResult:
        # Sends a user-facing account status notice after an administrator deactivates access.
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        subject = "Your Violyt Account Has Been Deactivated"
        actor_label = "the Platform Owner" if deactivated_by_platform_owner else "your Tenant Admin"
        contact_label = "the Platform Owner" if deactivated_by_platform_owner else "your Tenant Administrator"
        text_body = (
            f"Hello {greeting_name},\n\n"
            f"Your Violyt account has been deactivated by {actor_label}.\n\n"
            "You will no longer be able to access your account until it is reactivated.\n\n"
            f"If you believe this was done in error, please contact {contact_label}.\n\n"
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f"<p>Your Violyt account has been deactivated by {escape(actor_label)}.</p>"
            "<p>You will no longer be able to access your account until it is reactivated.</p>"
            f"<p>If you believe this was done in error, please contact {escape(contact_label)}.</p>"
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_user_deactivated_confirmation_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        deactivated_user_name: str,
        deactivated_user_role: str,
    ) -> EmailDeliveryResult:
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        escaped_user_name = escape(deactivated_user_name)
        escaped_user_role = escape(deactivated_user_role)
        subject = "User Account Deactivated"
        text_body = (
            f"Hello {greeting_name},\n\n"
            f'"{deactivated_user_name}" ({deactivated_user_role}) has been successfully deactivated.\n\n'
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f'<p>"{escaped_user_name}" ({escaped_user_role}) has been successfully deactivated.</p>'
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_platform_owner_user_deactivated_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        deactivated_user_name: str,
        deactivated_user_role: str,
        tenant_admin_name: str,
        tenant_name: str,
    ) -> EmailDeliveryResult:
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        escaped_user_name = escape(deactivated_user_name)
        escaped_user_role = escape(deactivated_user_role)
        escaped_admin_name = escape(tenant_admin_name)
        escaped_tenant_name = escape(tenant_name)
        subject = "User Account Deactivated"
        text_body = (
            f"Hello {greeting_name},\n\n"
            f'"{deactivated_user_name}" ({deactivated_user_role}) has been deactivated by '
            f'Tenant Admin "{tenant_admin_name}".\n\n'
            "Tenant:\n"
            f"{tenant_name}\n\n"
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f'<p>"{escaped_user_name}" ({escaped_user_role}) has been deactivated by '
            f'Tenant Admin "{escaped_admin_name}".</p>'
            "<p>Tenant:<br>"
            f"{escaped_tenant_name}</p>"
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_tenant_admin_deactivated_confirmation_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        tenant_admin_name: str,
        tenant_name: str,
    ) -> EmailDeliveryResult:
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        escaped_admin_name = escape(tenant_admin_name)
        escaped_tenant_name = escape(tenant_name)
        subject = "Tenant Admin Account Deactivated"
        text_body = (
            f"Hello {greeting_name},\n\n"
            f'Tenant Admin "{tenant_admin_name}" has been successfully deactivated.\n\n'
            "Tenant:\n"
            f"{tenant_name}\n\n"
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f'<p>Tenant Admin "{escaped_admin_name}" has been successfully deactivated.</p>'
            "<p>Tenant:<br>"
            f"{escaped_tenant_name}</p>"
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_account_reactivated_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        *,
        reactivated_by_platform_owner: bool = False,
    ) -> EmailDeliveryResult:
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        subject = "Your Violyt Account Has Been Reactivated"
        actor_label = "the Platform Owner" if reactivated_by_platform_owner else "your Tenant Admin"
        text_body = (
            f"Hello {greeting_name},\n\n"
            f"Your Violyt account has been reactivated by {actor_label}.\n\n"
            "You can now sign in and access your account again.\n\n"
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f"<p>Your Violyt account has been reactivated by {escape(actor_label)}.</p>"
            "<p>You can now sign in and access your account again.</p>"
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_user_reactivated_confirmation_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        reactivated_user_name: str,
        reactivated_user_role: str,
    ) -> EmailDeliveryResult:
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        escaped_user_name = escape(reactivated_user_name)
        escaped_user_role = escape(reactivated_user_role)
        subject = "User Account Reactivated"
        text_body = (
            f"Hello {greeting_name},\n\n"
            f'"{reactivated_user_name}" ({reactivated_user_role}) has been successfully reactivated.\n\n'
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f'<p>"{escaped_user_name}" ({escaped_user_role}) has been successfully reactivated.</p>'
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_platform_owner_user_reactivated_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        reactivated_user_name: str,
        reactivated_user_role: str,
        tenant_admin_name: str,
        tenant_name: str,
    ) -> EmailDeliveryResult:
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        escaped_user_name = escape(reactivated_user_name)
        escaped_user_role = escape(reactivated_user_role)
        escaped_admin_name = escape(tenant_admin_name)
        escaped_tenant_name = escape(tenant_name)
        subject = "User Account Reactivated"
        text_body = (
            f"Hello {greeting_name},\n\n"
            f'"{reactivated_user_name}" ({reactivated_user_role}) has been reactivated by '
            f'Tenant Admin "{tenant_admin_name}".\n\n'
            "Tenant:\n"
            f"{tenant_name}\n\n"
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f'<p>"{escaped_user_name}" ({escaped_user_role}) has been reactivated by '
            f'Tenant Admin "{escaped_admin_name}".</p>'
            "<p>Tenant:<br>"
            f"{escaped_tenant_name}</p>"
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_tenant_admin_reactivated_confirmation_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        tenant_admin_name: str,
        tenant_name: str,
    ) -> EmailDeliveryResult:
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        escaped_admin_name = escape(tenant_admin_name)
        escaped_tenant_name = escape(tenant_name)
        subject = "Tenant Admin Account Reactivated"
        text_body = (
            f"Hello {greeting_name},\n\n"
            f'Tenant Admin "{tenant_admin_name}" has been successfully reactivated.\n\n'
            "Tenant:\n"
            f"{tenant_name}\n\n"
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f'<p>Tenant Admin "{escaped_admin_name}" has been successfully reactivated.</p>'
            "<p>Tenant:<br>"
            f"{escaped_tenant_name}</p>"
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_review_comment_notification_email(
        self,
        recipient_email: str,
        commenter_name: str,
        comment_text: str,
        review_link: str,
        post_title: str | None = None,
    ) -> EmailDeliveryResult:
        # Sends a review-thread notice without changing the comment workflow result.
        title_label = post_title or "Shared image"
        subject = f"New comment on {title_label}"
        escaped_commenter_name = escape(commenter_name)
        escaped_comment_text = escape(comment_text)
        escaped_title_label = escape(title_label)
        escaped_review_link = escape(review_link)
        text_body = (
            f"{commenter_name} added a new comment on {title_label}.\n\n"
            f"Comment:\n{comment_text}\n\n"
            f"Open the review thread:\n{review_link}"
        )
        html_body = (
            f"<p><strong>{escaped_commenter_name}</strong> added a new comment on "
            f"<strong>{escaped_title_label}</strong>.</p>"
            f"<p>{escaped_comment_text}</p>"
            f'<p><a href="{escaped_review_link}" style="display:inline-block;padding:12px 20px;'
            "background:#3C2F8F;color:#ffffff;text-decoration:none;border-radius:8px;"
            '">Open Review Thread</a></p>'
            f"<p>If the button does not work, open this link:</p><p>{escaped_review_link}</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_review_mention_notification_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        sharer_name: str,
        review_link: str,
        post_title: str | None = None,
    ) -> EmailDeliveryResult:
        title_label = post_title or "Shared image"
        greeting_name = recipient_name or recipient_email
        subject = f"You were mentioned on {title_label}"
        escaped_greeting_name = escape(greeting_name)
        escaped_sharer_name = escape(sharer_name)
        escaped_title_label = escape(title_label)
        escaped_review_link = escape(review_link)
        text_body = (
            f"Hello {greeting_name},\n\n"
            f"{sharer_name} mentioned you on {title_label}.\n\n"
            f"Open the review thread:\n{review_link}"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f"<p><strong>{escaped_sharer_name}</strong> mentioned you on "
            f"<strong>{escaped_title_label}</strong>.</p>"
            f'<p><a href="{escaped_review_link}" style="display:inline-block;padding:12px 20px;'
            "background:#3C2F8F;color:#ffffff;text-decoration:none;border-radius:8px;"
            '">Open Review Thread</a></p>'
            f"<p>If the button does not work, open this link:</p><p>{escaped_review_link}</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_review_approved_notification_email(
        self,
        recipient_email: str,
        reviewer_name: str,
        review_link: str,
        post_title: str | None = None,
    ) -> EmailDeliveryResult:
        title_label = post_title or "Shared image"
        subject = f"{title_label} was approved"
        escaped_reviewer_name = escape(reviewer_name)
        escaped_title_label = escape(title_label)
        escaped_review_link = escape(review_link)
        text_body = (
            f"{reviewer_name} approved {title_label}.\n\n"
            f"Open the review thread:\n{review_link}"
        )
        html_body = (
            f"<p><strong>{escaped_reviewer_name}</strong> approved "
            f"<strong>{escaped_title_label}</strong>.</p>"
            f'<p><a href="{escaped_review_link}" style="display:inline-block;padding:12px 20px;'
            "background:#3C2F8F;color:#ffffff;text-decoration:none;border-radius:8px;"
            '">Open Review Thread</a></p>'
            f"<p>If the button does not work, open this link:</p><p>{escaped_review_link}</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_review_access_removed_notification_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        remover_name: str,
        post_title: str | None = None,
    ) -> EmailDeliveryResult:
        title_label = post_title or "Shared image"
        greeting_name = recipient_name or recipient_email
        subject = f"Access removed for {title_label}"
        escaped_greeting_name = escape(greeting_name)
        escaped_remover_name = escape(remover_name)
        escaped_title_label = escape(title_label)
        text_body = (
            f"Hello {greeting_name},\n\n"
            f"{remover_name} removed your access to {title_label}.\n\n"
            "You will no longer be able to open this review thread."
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f"<p><strong>{escaped_remover_name}</strong> removed your access to "
            f"<strong>{escaped_title_label}</strong>.</p>"
            "<p>You will no longer be able to open this review thread.</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def send_brand_space_updated_email(
        self,
        recipient_email: str,
        recipient_name: str | None,
        brand_space_name: str,
    ) -> EmailDeliveryResult:
        greeting_name = recipient_name or recipient_email
        escaped_greeting_name = escape(greeting_name)
        escaped_brand_space_name = escape(brand_space_name)
        subject = "Brand Space Updated"
        text_body = (
            f"Hello {greeting_name},\n\n"
            f'The Brand Space "{brand_space_name}" has been updated.\n\n'
            "The latest changes will be applied to all future creative outputs generated using this Brand Space.\n\n"
            "If you need to review the updated Brand Space details, please sign in to Violyt.\n\n"
            "Regards,\n"
            "Violyt Team"
        )
        html_body = (
            f"<p>Hello {escaped_greeting_name},</p>"
            f'<p>The Brand Space "{escaped_brand_space_name}" has been updated.</p>'
            "<p>The latest changes will be applied to all future creative outputs generated using this Brand Space.</p>"
            "<p>If you need to review the updated Brand Space details, please sign in to Violyt.</p>"
            "<p>Regards,<br>Violyt Team</p>"
        )
        return self._send_email(recipient_email, subject, text_body, html_body)

    def _send_email(
        self,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> EmailDeliveryResult:
        # Internal helper for send email; it keeps the public service method focused on orchestration instead of
        # low-level shaping.
        if not self.is_configured():
            logger.warning("SMTP is not configured. Skipping email delivery for %s.", recipient_email)
            return EmailDeliveryResult(
                attempted=False,
                delivered=False,
                recipient_email=recipient_email,
                reason="SMTP is not configured.",
            )

        message = EmailMessage()
        from_email = self.settings.smtp_from_email or self.settings.smtp_username or "noreply@violyt.local"
        from_name = self.settings.smtp_from_name
        message["Subject"] = subject
        message["From"] = f"{from_name} <{from_email}>"
        message["To"] = recipient_email
        message.set_content(text_body)
        if html_body:
            message.add_alternative(html_body, subtype="html")

        context = ssl.create_default_context()
        # Keeps the risky I/O or integration boundary contained so callers receive project-level errors
        # instead of raw library failures.
        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=20) as smtp:
                smtp.ehlo()
                if self.settings.smtp_use_tls:
                    smtp.starttls(context=context)
                    smtp.ehlo()
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
                smtp.send_message(message)
        except smtplib.SMTPAuthenticationError as exc:
            logger.warning("Email delivery failed for %s: %s", recipient_email, exc)
            return EmailDeliveryResult(
                attempted=True,
                delivered=False,
                recipient_email=recipient_email,
                reason="SMTP authentication failed. Check the sender email password or app password.",
            )
        except smtplib.SMTPRecipientsRefused as exc:
            logger.warning("Email delivery failed for %s: %s", recipient_email, exc)
            return EmailDeliveryResult(
                attempted=True,
                delivered=False,
                recipient_email=recipient_email,
                reason="The recipient email address was rejected by the mail server.",
            )
        except (smtplib.SMTPConnectError, TimeoutError, OSError) as exc:
            logger.warning("Email delivery failed for %s: %s", recipient_email, exc)
            return EmailDeliveryResult(
                attempted=True,
                delivered=False,
                recipient_email=recipient_email,
                reason="Could not connect to the SMTP server.",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Email delivery failed for %s: %s", recipient_email, exc)
            return EmailDeliveryResult(
                attempted=True,
                delivered=False,
                recipient_email=recipient_email,
                reason=str(exc) or "Email delivery failed.",
            )

        return EmailDeliveryResult(
            attempted=True,
            delivered=True,
            recipient_email=recipient_email,
            reason=None,
        )
