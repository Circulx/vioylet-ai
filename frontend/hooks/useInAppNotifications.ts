"use client";

import { useEffect, useMemo, useState } from "react";

export type InAppNotification = {
  id: string;
  recipientUserId: string;
  title: string;
  message: string;
  createdAt: string;
  unread: boolean;
};

const STORAGE_PREFIX = "violyt:in-app-notifications:";
const NOTIFICATION_EVENT = "violyt:in-app-notifications-updated";

type NotificationCreateInput = {
  title: string;
  message: string;
};

function storageKey(userId: string) {
  return `${STORAGE_PREFIX}${userId}`;
}

function parseNotifications(value: string | null): InAppNotification[] {
  if (!value) {
    return [];
  }
  try {
    const parsed = JSON.parse(value);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((item): item is InAppNotification =>
      typeof item?.id === "string" &&
      typeof item?.recipientUserId === "string" &&
      typeof item?.title === "string" &&
      typeof item?.message === "string" &&
      typeof item?.createdAt === "string" &&
      typeof item?.unread === "boolean",
    );
  } catch {
    return [];
  }
}

function readNotifications(userId: string) {
  if (typeof window === "undefined") {
    return [];
  }
  return parseNotifications(window.localStorage.getItem(storageKey(userId)));
}

function writeNotifications(userId: string, notifications: InAppNotification[]) {
  window.localStorage.setItem(storageKey(userId), JSON.stringify(notifications));
  window.dispatchEvent(new CustomEvent(NOTIFICATION_EVENT, { detail: { userId } }));
}

function createId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function addInAppNotification(userId: string, input: NotificationCreateInput) {
  if (typeof window === "undefined" || !userId) {
    return null;
  }
  const notification: InAppNotification = {
    id: createId(),
    recipientUserId: userId,
    title: input.title,
    message: input.message,
    createdAt: new Date().toISOString(),
    unread: true,
  };
  writeNotifications(userId, [notification, ...readNotifications(userId)]);
  return notification;
}

export function addInAppNotificationForRecipients(userIds: string[], input: NotificationCreateInput) {
  const uniqueUserIds = Array.from(new Set(userIds.map((userId) => userId.trim()).filter(Boolean)));
  return uniqueUserIds
    .map((userId) => addInAppNotification(userId, input))
    .filter((notification): notification is InAppNotification => Boolean(notification));
}

export function clearInAppNotifications(userId: string) {
  if (typeof window === "undefined" || !userId) {
    return;
  }
  writeNotifications(userId, []);
}

export function removeInAppNotification(userId: string, notificationId: string) {
  if (typeof window === "undefined" || !userId || !notificationId) {
    return;
  }
  writeNotifications(
    userId,
    readNotifications(userId).filter((notification) => notification.id !== notificationId),
  );
}

export function useInAppNotifications(userId?: string) {
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!userId || typeof window === "undefined") {
      return;
    }
    const handleUpdate = (event: Event) => {
      const detail = event instanceof CustomEvent ? event.detail : null;
      if (!detail?.userId || detail.userId === userId) {
        setVersion((current) => current + 1);
      }
    };
    const handleStorage = (event: StorageEvent) => {
      if (event.key === storageKey(userId)) {
        setVersion((current) => current + 1);
      }
    };
    window.addEventListener(NOTIFICATION_EVENT, handleUpdate);
    window.addEventListener("storage", handleStorage);
    return () => {
      window.removeEventListener(NOTIFICATION_EVENT, handleUpdate);
      window.removeEventListener("storage", handleStorage);
    };
  }, [userId]);

  const notifications = useMemo(() => {
    if (!userId) {
      return [];
    }
    return readNotifications(userId);
  }, [userId, version]);

  return {
    notifications,
    remove: (notificationId: string) => {
      if (userId) {
        removeInAppNotification(userId, notificationId);
      }
    },
    clear: () => {
      if (userId) {
        clearInAppNotifications(userId);
      }
    },
  };
}
