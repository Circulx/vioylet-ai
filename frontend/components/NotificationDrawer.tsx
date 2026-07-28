"use client"

import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { API } from "@/lib/api/endpoints"
import { request } from "@/lib/api/request"
import { NOTIFICATION_REFETCH_INTERVAL_MS } from "@/lib/notification-queries"
import { useGetMe } from "@/hooks/useUser"
import { useInAppNotifications } from "@/hooks/useInAppNotifications"
import { ReactNode, useEffect, useState } from "react"
import { X } from "lucide-react"

function getNotificationKey(source: "server" | "local", id: string) {
  return `${source}-${id}`
}

const WELCOME_CELEBRATION_STORAGE_KEY = "violyt:celebrated-welcome-notifications"

function isWelcomeNotification(title: string) {
  return title.toLowerCase().includes("welcome to violyt")
}

function getNotificationIcon(title: string, message: string) {
  const content = `${title} ${message}`.toLowerCase()

  if (isWelcomeNotification(title)) return "\uD83C\uDF89"
  if (content.includes("deactivated")) return "\u26D4"
  if (content.includes("reactivated")) return "\uD83D\uDD04"
  if (content.includes("activated")) return "\uD83D\uDC65"
  if (content.includes("profile updated")) return "\uD83D\uDC64"
  if (content.includes("password")) return "\uD83D\uDD10"
  if (content.includes("two-factor") || content.includes("2fa") || content.includes("security update")) return "\uD83D\uDEE1\uFE0F"
  if (content.includes("new comment") || content.includes("commented")) return "\uD83D\uDCE9"
  if (content.includes("approved")) return "\u2705"
  if (content.includes("published")) return "\uD83D\uDE80"
  if (content.includes("updated")) return "\uD83D\uDCDD"
  if (content.includes("assigned") || content.includes("access removed")) return "\uD83D\uDCE6"
  if (content.includes("capacity") || content.includes("usage")) return "\uD83D\uDCCA"
  if (content.includes("warning") || content.includes("exhausted") || content.includes("limit")) return "\u26A0\uFE0F"

  return "\u2139\uFE0F"
}

function readCelebratedWelcomeKeys(userId?: string) {
  if (typeof window === "undefined" || !userId) {
    return new Set<string>()
  }

  try {
    const parsed = JSON.parse(window.localStorage.getItem(`${WELCOME_CELEBRATION_STORAGE_KEY}:${userId}`) || "[]")
    return new Set(Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === "string") : [])
  } catch {
    return new Set<string>()
  }
}

function writeCelebratedWelcomeKeys(userId: string, keys: Set<string>) {
  if (typeof window === "undefined") {
    return
  }

  window.localStorage.setItem(`${WELCOME_CELEBRATION_STORAGE_KEY}:${userId}`, JSON.stringify([...keys]))
}

function formatNotificationTimestamp(value: string) {
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) {
    return ""
  }
  const diffMinutes = Math.max(0, Math.round((Date.now() - timestamp) / 60000))
  if (diffMinutes < 1) {
    return "Just now"
  }
  if (diffMinutes < 60) {
    return `${diffMinutes} min ago`
  }
  const diffHours = Math.round(diffMinutes / 60)
  if (diffHours < 24) {
    return `${diffHours} hr ago`
  }
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value))
}

export function NotificationDrawer({ children }: { children: ReactNode }) {
  const { data: user } = useGetMe()
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [highlightedUnreadKeys, setHighlightedUnreadKeys] = useState<Set<string>>(new Set())
  const [celebratingWelcomeKeys, setCelebratingWelcomeKeys] = useState<Set<string>>(new Set())
  const {
    notifications: localNotifications,
    remove: removeLocalNotification,
    clear: clearLocalNotifications,
    markAllRead: markLocalNotificationsRead,
  } = useInAppNotifications(user?.id)
  const { data: serverNotifications = [], refetch: refetchServerNotifications } = useQuery({
    queryKey: ["notifications", user?.id],
    enabled: Boolean(user?.id),
    queryFn: () => request(API.NOTIFICATIONS.LIST),
    refetchOnWindowFocus: "always",
    refetchInterval: user?.id ? NOTIFICATION_REFETCH_INTERVAL_MS : false,
  })
  const markServerNotificationsRead = useMutation({
    mutationFn: () => request(API.NOTIFICATIONS.MARK_READ),
    onMutate: async () => {
      await Promise.all([
        queryClient.cancelQueries({ queryKey: ["notifications", user?.id] }),
        queryClient.cancelQueries({ queryKey: ["notifications", user?.id, "unread-count"] }),
      ])
      queryClient.setQueryData<typeof serverNotifications>(["notifications", user?.id], (current) =>
        (current || []).map((notification) => ({
          ...notification,
          unread: false,
        })),
      )
      queryClient.setQueryData(["notifications", user?.id, "unread-count"], { unread_count: 0 })
    },
    onSettled: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["notifications", user?.id] }),
        queryClient.invalidateQueries({ queryKey: ["notifications", user?.id, "unread-count"] }),
      ])
    },
  })
  const clearServerNotifications = useMutation({
    mutationFn: () => request(API.NOTIFICATIONS.CLEAR),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["notifications", user?.id] }),
        queryClient.invalidateQueries({ queryKey: ["notifications", user?.id, "unread-count"] }),
      ])
    },
  })
  const deleteServerNotification = useMutation({
    mutationFn: (notificationId: string) =>
      request(API.NOTIFICATIONS.DELETE, {
        pathParams: notificationId,
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["notifications", user?.id] }),
        queryClient.invalidateQueries({ queryKey: ["notifications", user?.id, "unread-count"] }),
      ])
    },
  })
  const notifications = [
    ...serverNotifications.map((notification) => ({
      id: notification.id,
      source: "server" as const,
      title: notification.title,
      message: notification.message,
      createdAt: notification.created_at,
      unread: notification.unread,
    })),
    ...localNotifications.map((notification) => ({
      id: notification.id,
      source: "local" as const,
      title: notification.title,
      message: notification.message,
      createdAt: notification.createdAt,
      unread: notification.unread,
    })),
  ].sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime())

  const handleClearAll = () => {
    clearLocalNotifications()
    if (user?.id) {
      clearServerNotifications.mutate()
    }
  }

  const handleDismissNotification = (notification: (typeof notifications)[number]) => {
    if (notification.source === "local") {
      removeLocalNotification(notification.id)
      return
    }
    deleteServerNotification.mutate(notification.id)
  }

  useEffect(() => {
    if (!celebratingWelcomeKeys.size) {
      return
    }

    const timeout = window.setTimeout(() => {
      setCelebratingWelcomeKeys(new Set())
    }, 3600)

    return () => window.clearTimeout(timeout)
  }, [celebratingWelcomeKeys])

  return (
    <Sheet
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (!nextOpen) {
          setHighlightedUnreadKeys(new Set())
          return
        }
        const unreadKeys = notifications
          .filter((notification) => notification.unread)
          .map((notification) => getNotificationKey(notification.source, notification.id))
        setHighlightedUnreadKeys(new Set(unreadKeys))
        const celebratedWelcomeKeys = readCelebratedWelcomeKeys(user?.id)
        const welcomeKeysToCelebrate = notifications
          .filter((notification) => notification.unread && isWelcomeNotification(notification.title))
          .map((notification) => getNotificationKey(notification.source, notification.id))
          .filter((notificationKey) => !celebratedWelcomeKeys.has(notificationKey))
        if (welcomeKeysToCelebrate.length && user?.id) {
          const nextCelebratedWelcomeKeys = new Set([...celebratedWelcomeKeys, ...welcomeKeysToCelebrate])
          writeCelebratedWelcomeKeys(user.id, nextCelebratedWelcomeKeys)
          setCelebratingWelcomeKeys(new Set(welcomeKeysToCelebrate))
        }
        if (user?.id) {
          markLocalNotificationsRead()
          markServerNotificationsRead.mutate()
          void refetchServerNotifications()
        }
      }}
    >
      <SheetTrigger asChild>
        {children}
      </SheetTrigger>
      <SheetContent className="overflow-hidden font-dmSans">
        <SheetHeader>
          <SheetTitle className="text-primary text-2xl font-bold">Notification</SheetTitle>
          <SheetDescription className="sr-only">
            View your recent notifications and updates.
          </SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 pr-2 pb-2">
          {notifications.length ? (
            notifications.map((notification) => {
              const notificationKey = getNotificationKey(notification.source, notification.id)
              const isVisuallyUnread = notification.unread || highlightedUnreadKeys.has(notificationKey)
              const isWelcome = isWelcomeNotification(notification.title)
              const isCelebratingWelcome = celebratingWelcomeKeys.has(notificationKey)
              const notificationIcon = getNotificationIcon(notification.title, notification.message)
              const displayTitle = isWelcome ? "Welcome to Violyt!" : notification.title
              const displayMessage = isWelcome
                ? "Welcome to Violyt! Your account has been activated successfully. We're excited to have you on board."
                : notification.message
              return (
                <div
                  key={notificationKey}
                  className={`relative overflow-hidden rounded-[6px] border border-[#DCDCDC] p-4 shadow-sm ${isVisuallyUnread ? "bg-[#EEF0F6]" : "bg-white"} ${isCelebratingWelcome ? "notification-welcome-celebration" : ""}`}
                >
                {isCelebratingWelcome ? (
                  <div className="pointer-events-none absolute inset-0" aria-hidden="true">
                    <span className="notification-confetti notification-confetti-a">{"\u2726"}</span>
                    <span className="notification-confetti notification-confetti-b">{"\u2022"}</span>
                    <span className="notification-confetti notification-confetti-c">{"\u2727"}</span>
                    <span className="notification-confetti notification-confetti-d">{"\u2726"}</span>
                  </div>
                ) : null}
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <div className="flex min-w-0 flex-1 items-start gap-2">
                        {notification.unread ? <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-primary" aria-label="Unread" /> : null}
                        <h1 className="min-w-0 whitespace-normal break-words text-base font-manrope text-primary font-medium" title={displayTitle}>{notificationIcon} {displayTitle}</h1>
                      </div>
                      <span className="shrink-0 text-xs text-gray-400">{formatNotificationTimestamp(notification.createdAt)}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-xs text-[#525252] transition hover:bg-slate-100 hover:text-slate-900"
                    aria-label={`Remove ${displayTitle} notification`}
                    onClick={() => handleDismissNotification(notification)}
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-2 text-sm leading-5 text-[#525252]">{displayMessage}</p>
                </div>
              )
            })
          ) : (
            <p className="py-6 text-sm text-[#525252]">No notifications yet.</p>
          )}
        </div>
        <SheetFooter>
          <SheetClose asChild>
            <Button variant="outline" className="w-full" onClick={handleClearAll}>Clear All</Button>
          </SheetClose>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
