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
import { ReactNode, useState } from "react"
import { X } from "lucide-react"

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
  const { notifications: localNotifications, remove: removeLocalNotification, clear: clearLocalNotifications } = useInAppNotifications(user?.id)
  const { data: serverNotifications = [], refetch: refetchServerNotifications } = useQuery({
    queryKey: ["notifications", user?.id],
    enabled: Boolean(user?.id),
    queryFn: () => request(API.NOTIFICATIONS.LIST),
    refetchOnWindowFocus: "always",
    refetchInterval: user?.id ? 30000 : false,
  })
  const clearServerNotifications = useMutation({
    mutationFn: () => request(API.NOTIFICATIONS.CLEAR),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications", user?.id] })
    },
  })
  const deleteServerNotification = useMutation({
    mutationFn: (notificationId: string) =>
      request(API.NOTIFICATIONS.DELETE, {
        pathParams: notificationId,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications", user?.id] })
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

  return (
    <Sheet
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen)
        if (nextOpen && user?.id) {
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
            notifications.map((notification) => (
              <div key={`${notification.source}-${notification.id}`} className="rounded-[6px] border border-[#DCDCDC] bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex min-w-0 flex-1 items-center gap-2">
                    {notification.unread ? <span className="h-2 w-2 shrink-0 rounded-full bg-primary" aria-label="Unread" /> : null}
                    <h1 className="truncate text-lg text-primary font-medium">{notification.title}</h1>
                    <span className="shrink-0 text-sm text-gray-400">{formatNotificationTimestamp(notification.createdAt)}</span>
                  </div>
                  <button
                    type="button"
                    className="flex h-6 w-6 shrink-0 items-center justify-center rounded-xs text-[#525252] transition hover:bg-slate-100 hover:text-slate-900"
                    aria-label={`Remove ${notification.title} notification`}
                    onClick={() => handleDismissNotification(notification)}
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-2 text-sm leading-5 text-[#525252]">{notification.message}</p>
              </div>
            ))
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
