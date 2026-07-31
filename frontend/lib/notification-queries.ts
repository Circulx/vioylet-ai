import type { QueryClient } from "@tanstack/react-query";

export const NOTIFICATION_REFETCH_INTERVAL_MS = 5000;

export function refreshNotificationQueries(queryClient: QueryClient) {
  return queryClient.invalidateQueries({ queryKey: ["notifications"] });
}
