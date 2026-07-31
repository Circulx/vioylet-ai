"use client";

import { Switch } from "@/components/ui/switch";

export function NotificationPreferenceControls({
    emailEnabled,
    inAppEnabled,
    disabled = false,
    onEmailChange,
    onInAppChange,
}: {
    emailEnabled: boolean;
    inAppEnabled: boolean;
    disabled?: boolean;
    onEmailChange: (checked: boolean) => void;
    onInAppChange: (checked: boolean) => void;
}) {
    return (
        <div>
            <h2 className="text-base font-medium text-black">Notifications</h2>
            <p className="mt-1 text-sm text-[#6B7280]">Enable or disable alerts and updates</p>

            <div className="mt-4 space-y-3">
                <NotificationPreferenceRow
                    title="Email notification"
                    checked={emailEnabled}
                    disabled={disabled}
                    onCheckedChange={onEmailChange}
                />
                <NotificationPreferenceRow
                    title="In-app notification"
                    checked={inAppEnabled}
                    disabled={disabled}
                    onCheckedChange={onInAppChange}
                />
            </div>
        </div>
    );
}

function NotificationPreferenceRow({
    title,
    checked,
    disabled,
    onCheckedChange,
}: {
    title: string;
    checked: boolean;
    disabled: boolean;
    onCheckedChange: (checked: boolean) => void;
}) {
    return (
        <div className="flex w-fit items-center gap-4">
            <p className="w-32 text-sm font-normal text-[#6B7280]">{title}</p>
            <Switch
                checked={checked}
                disabled={disabled}
                onCheckedChange={onCheckedChange}
                aria-label={title}
            />
        </div>
    );
}
