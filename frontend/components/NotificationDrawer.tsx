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
import { useGetMe } from "@/hooks/useUser"
import { useInAppNotifications } from "@/hooks/useInAppNotifications"
import { ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  Archive,
  BadgeCheck,
  BarChart3,
  Bell,
  CheckCircle2,
  FolderCheck,
  KeyRound,
  LockKeyhole,
  Mail,
  MessageCircle,
  PartyPopper,
  Pencil,
  Rocket,
  RotateCcw,
  Siren,
  Sparkles,
  Trash2,
  UnlockKeyhole,
  TriangleAlert,
  UserCheck,
  UserCog,
  UserX,
  X,
  type LucideIcon,
} from "lucide-react"

function getNotificationKey(source: "server" | "local", id: string) {
  return `${source}-${id}`
}

type NotificationAnimationVariant = "celebration" | "welcome" | "warning" | "critical" | null
type NotificationIconConfig = { Icon: LucideIcon; className: string }

function isWelcomeNotification(title: string) {
  return title.toLowerCase().includes("welcome to violyt")
}

function getNotificationAnimationVariant(title: string, message: string): NotificationAnimationVariant {
  const normalizedTitle = title.toLowerCase()
  const content = `${title} ${message}`.toLowerCase()

  if (isWelcomeNotification(title)) return "welcome"
  if (
    normalizedTitle.includes("super user activated") ||
    normalizedTitle.includes("tenant admin activated") ||
    normalizedTitle.includes("brand user activated")
  ) {
    return "celebration"
  }
  if (content.includes("usage critical") || content.includes("critical usage") || content.includes("usage exhausted") || content.includes("exhausted")) {
    return "critical"
  }
  if (content.includes("usage warning") || content.includes("capacity warning") || (content.includes("usage") && (content.includes("warning") || content.includes("approach") || content.includes("limit")))) {
    return "warning"
  }

  return null
}

function getNotificationIconAnimationClass(title: string, message: string) {
  const normalizedTitle = title.toLowerCase()
  const content = `${title} ${message}`.toLowerCase()

  if (isWelcomeNotification(title)) return "notification-icon-celebrate"
  if (content.includes("usage critical") || content.includes("critical usage") || content.includes("usage exhausted") || content.includes("exhausted")) return "notification-icon-alert-shake"
  if (content.includes("capacity usage updated") || content.includes("usage limit updated")) return "notification-icon-grow-in"
  if (content.includes("brand capacity usage warning") || content.includes("capacity allocation warning") || content.includes("usage warning") || content.includes("capacity warning") || (content.includes("usage") && (content.includes("warning") || content.includes("approach") || content.includes("limit")))) return "notification-icon-slow-pulse"
  if (content.includes("brand space") && content.includes("deleted")) return "notification-icon-bounce"
  if (content.includes("brand space") && content.includes("archived")) return "notification-icon-slide-settle"
  if (content.includes("brand space") && content.includes("restored")) return "notification-icon-rotate-in"
  if (content.includes("brand space") && content.includes("published")) return "notification-icon-rocket-lift"
  if (content.includes("brand space") && content.includes("created")) return "notification-icon-celebrate"
  if (content.includes("brand space") && (content.includes("assigned") || content.includes("granted access") || content.includes("access removed"))) return "notification-icon-bounce"
  if (content.includes("two-factor") && content.includes("disabled")) return "notification-icon-unlock-pop"
  if (content.includes("two-factor") || content.includes("2fa") || content.includes("security update")) return "notification-icon-lock-snap"
  if (content.includes("deactivated")) return "notification-icon-gentle-shake"
  if (content.includes("reactivated")) return "notification-icon-rotate-in"
  if (normalizedTitle.includes("activated")) return "notification-icon-pop-scale"
  if (content.includes("role updated")) return "notification-icon-smooth-rotate"
  if (content.includes("profile updated")) return "notification-icon-pencil-draw"
  if (content.includes("password")) return "notification-icon-key-rotate"
  if (content.includes("new comment") || content.includes("commented")) return "notification-icon-chat-pop"
  if (content.includes("approved")) return "notification-icon-check-pop"
  if (content.includes("file") && (content.includes("synced") || content.includes("ready"))) return "notification-icon-bounce"
  if (content.includes("email")) return "notification-icon-envelope-pop"
  if (content.includes("capacity") || content.includes("usage")) return "notification-icon-grow-in"
  if (content.includes("published") || content.includes("created") || content.includes("successful") || content.includes("completed")) return "notification-icon-pop-scale"
  if (content.includes("updated")) return "notification-icon-pencil-draw"

  return "notification-icon-bell-ring"
}

function getNotificationIcon(title: string, message: string): NotificationIconConfig {
  const normalizedTitle = title.toLowerCase()
  const content = `${title} ${message}`.toLowerCase()

  if (isWelcomeNotification(title)) return { Icon: PartyPopper, className: "text-fuchsia-500" }
  if (content.includes("usage critical") || content.includes("critical usage") || content.includes("usage exhausted") || content.includes("exhausted")) {
    return { Icon: Siren, className: "text-red-600" }
  }
  if (content.includes("usage warning") || content.includes("capacity warning") || (content.includes("usage") && (content.includes("warning") || content.includes("approach") || content.includes("limit")))) {
    return { Icon: TriangleAlert, className: "text-orange-500" }
  }
  if (content.includes("brand space") && content.includes("deleted")) return { Icon: Trash2, className: "text-red-500" }
  if (content.includes("brand space") && content.includes("archived")) return { Icon: Archive, className: "text-slate-500" }
  if (content.includes("brand space") && content.includes("restored")) return { Icon: RotateCcw, className: "text-emerald-600" }
  if (content.includes("brand space") && content.includes("published")) return { Icon: Rocket, className: "text-violet-500" }
  if (content.includes("brand space") && content.includes("created")) return { Icon: PartyPopper, className: "text-fuchsia-500" }
  if (content.includes("brand space") && (content.includes("assigned") || content.includes("granted access"))) {
    return { Icon: FolderCheck, className: "text-emerald-600" }
  }
  if (content.includes("brand space") && content.includes("access removed")) return { Icon: FolderCheck, className: "text-amber-600" }
  if (content.includes("two-factor") && content.includes("disabled")) return { Icon: UnlockKeyhole, className: "text-orange-500" }
  if (content.includes("two-factor") || content.includes("2fa") || content.includes("security update")) return { Icon: LockKeyhole, className: "text-emerald-600" }
  if (content.includes("deactivated")) return { Icon: UserX, className: "text-red-500" }
  if (content.includes("reactivated")) return { Icon: RotateCcw, className: "text-emerald-600" }
  if (normalizedTitle.includes("activated")) return { Icon: UserCheck, className: "text-emerald-600" }
  if (content.includes("role updated")) return { Icon: UserCog, className: "text-sky-600" }
  if (content.includes("profile updated")) return { Icon: Pencil, className: "text-blue-600" }
  if (content.includes("password")) return { Icon: KeyRound, className: "text-amber-600" }
  if (content.includes("new comment") || content.includes("commented")) return { Icon: MessageCircle, className: "text-cyan-600" }
  if (content.includes("approved")) return { Icon: BadgeCheck, className: "text-emerald-600" }
  if (content.includes("file") && (content.includes("synced") || content.includes("ready"))) return { Icon: FolderCheck, className: "text-emerald-600" }
  if (content.includes("email")) return { Icon: Mail, className: "text-sky-600" }
  if (content.includes("capacity") || content.includes("usage")) return { Icon: BarChart3, className: "text-indigo-500" }
  if (content.includes("completed") || content.includes("successful")) return { Icon: CheckCircle2, className: "text-emerald-600" }
  if (content.includes("published")) return { Icon: Rocket, className: "text-violet-500" }
  if (content.includes("created")) return { Icon: Sparkles, className: "text-violet-500" }
  if (content.includes("updated")) return { Icon: Pencil, className: "text-blue-600" }

  return { Icon: Bell, className: "text-primary" }
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
  const drawerOpenRef = useRef(false)
  const hasProcessedOpenRef = useRef(false)
  const [highlightedUnreadKeys, setHighlightedUnreadKeys] = useState<Set<string>>(new Set())
  const {
    notifications: localNotifications,
    remove: removeLocalNotification,
    clear: clearLocalNotifications,
    markAllRead: markLocalNotificationsRead,
  } = useInAppNotifications(user?.id)
  const {
    data: serverNotifications = [],
    isFetching: isFetchingServerNotifications,
    isSuccess: hasLoadedServerNotifications,
  } = useQuery({
    queryKey: ["notifications", user?.id],
    enabled: Boolean(user?.id) && open,
    queryFn: () => request(API.NOTIFICATIONS.LIST),
    refetchOnWindowFocus: false,
  })
  const markServerNotificationsRead = useMutation({
    mutationFn: () => request(API.NOTIFICATIONS.MARK_READ),
    onMutate: async () => {
      const previousServerNotifications = queryClient.getQueryData<typeof serverNotifications>(["notifications", user?.id])
      const previousUnreadCount = queryClient.getQueryData(["notifications", user?.id, "unread-count"])
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
      return { previousServerNotifications, previousUnreadCount }
    },
    onError: (_error, _variables, context) => {
      queryClient.setQueryData(["notifications", user?.id], context?.previousServerNotifications)
      queryClient.setQueryData(["notifications", user?.id, "unread-count"], context?.previousUnreadCount)
    },
    onSettled: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications", user?.id, "unread-count"] })
    },
  })
  const clearServerNotifications = useMutation({
    mutationFn: () => request(API.NOTIFICATIONS.CLEAR),
    onSuccess: async () => {
      queryClient.setQueryData(["notifications", user?.id], [])
      queryClient.setQueryData(["notifications", user?.id, "unread-count"], { unread_count: 0 })
      await queryClient.invalidateQueries({ queryKey: ["notifications", user?.id, "unread-count"] })
    },
  })
  const deleteServerNotification = useMutation({
    mutationFn: (notificationId: string) =>
      request(API.NOTIFICATIONS.DELETE, {
        pathParams: notificationId,
      }),
    onSuccess: async (_response, notificationId) => {
      queryClient.setQueryData<typeof serverNotifications>(["notifications", user?.id], (current) =>
        (current || []).filter((notification) => notification.id !== notificationId),
      )
      await queryClient.invalidateQueries({ queryKey: ["notifications", user?.id, "unread-count"] })
    },
  })
  const notifications = useMemo(() => [
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
  ].sort((left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()), [localNotifications, serverNotifications])

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
  const playNotificationCardAnimations = useCallback(() => {
    if (!user?.id) {
      return
    }
    const playedAnimationKeys = readCelebratedWelcomeKeys(user.id)
    const animationKeysToPlay = notifications
      .filter((notification) => notification.unread && getNotificationAnimationVariant(notification.title, notification.message))
      .map((notification) => getNotificationKey(notification.source, notification.id))
      .filter((notificationKey) => !playedAnimationKeys.has(notificationKey))
    if (!animationKeysToPlay.length) {
      return
    }
    const nextPlayedAnimationKeys = new Set([...playedAnimationKeys, ...animationKeysToPlay])
    writeCelebratedWelcomeKeys(user.id, nextPlayedAnimationKeys)
    setAnimatingNotificationKeys((current) => new Set([...current, ...animationKeysToPlay]))
  }, [notifications, user])

  useEffect(() => {
    if (!open) {
      return
    }
    playNotificationCardAnimations()
  }, [notifications, open, playNotificationCardAnimations])

  useEffect(() => {
    if (
      !open ||
      !user?.id ||
      !hasLoadedServerNotifications ||
      isFetchingServerNotifications ||
      hasProcessedOpenRef.current
    ) {
      return
    }

    hasProcessedOpenRef.current = true
    const unreadServerKeys = serverNotifications
      .filter((notification) => notification.unread)
      .map((notification) => getNotificationKey("server", notification.id))
    if (!unreadServerKeys.length) {
      return
    }

    queueMicrotask(() => {
      if (drawerOpenRef.current) {
        setHighlightedUnreadKeys((current) => new Set([...current, ...unreadServerKeys]))
      }
      markServerNotificationsRead.mutate()
    })
  }, [
    hasLoadedServerNotifications,
    isFetchingServerNotifications,
    markServerNotificationsRead,
    open,
    serverNotifications,
    user?.id,
  ])

  useEffect(() => {
    if (!animatingNotificationKeys.size) {
      return
    }

    const timeout = window.setTimeout(() => {
      setAnimatingNotificationKeys(new Set())
    }, 4800)

    return () => window.clearTimeout(timeout)
  }, [animatingNotificationKeys])

  return (
    <Sheet
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        drawerOpenRef.current = nextOpen
        hasProcessedOpenRef.current = false
        if (!nextOpen) {
          setHighlightedUnreadKeys(new Set())
          return
        }
        const unreadKeys = notifications
          .filter((notification) => notification.unread)
          .map((notification) => getNotificationKey(notification.source, notification.id))
        setHighlightedUnreadKeys(new Set(unreadKeys))
        if (user?.id) {
          markLocalNotificationsRead()
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
              const animationVariant = getNotificationAnimationVariant(notification.title, notification.message)
              const cardBackgroundClass = animationVariant === "critical"
                ? "bg-[#FEF2F2] border-[#FCA5A5]"
                : animationVariant === "warning"
                  ? "bg-[#FFF7ED] border-[#FDBA74]"
                  : isVisuallyUnread ? "bg-[#EEF0F6] border-[#DCDCDC]" : "bg-white border-[#DCDCDC]"
              const shouldAnimateNotificationIcon = isVisuallyUnread
              const newNotificationIconAnimationClass = shouldAnimateNotificationIcon
                ? getNotificationIconAnimationClass(notification.title, notification.message)
                : ""
              const notificationIcon = getNotificationIcon(notification.title, notification.message)
              const NotificationIcon = notificationIcon.Icon
              const displayTitle = isWelcome ? "Welcome to Violyt!" : notification.title
              const displayMessage = isWelcome
                ? "Welcome to Violyt! Your account has been activated successfully. We're excited to have you on board."
                : notification.message
              return (
                <div
                  key={notificationKey}
                  className={`relative overflow-hidden rounded-[6px] border p-4 shadow-sm ${cardBackgroundClass}`}
                >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <div className="flex min-w-0 flex-1 items-start gap-2">
                        {notification.unread ? <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-primary" aria-label="Unread" /> : null}
                        <h1 className="min-w-0 whitespace-normal break-words text-base font-manrope text-primary font-medium" title={displayTitle}><span className={`inline-flex align-[-2px] ${newNotificationIconAnimationClass}`} aria-hidden="true"><NotificationIcon className={`h-4 w-4 ${notificationIcon.className}`} strokeWidth={2.2} /></span> {displayTitle}</h1>
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
