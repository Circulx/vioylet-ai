"use client";

import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "@/components/ui/use-toast";
import { useBrands } from "@/hooks/useBrands";
import type { BrandAttachmentResponse, UiUser } from "@/lib/api/contracts";
import { listBrandSpaceAttachments } from "@/lib/brand-space-persistence";
import { NOTIFICATION_REFETCH_INTERVAL_MS } from "@/lib/notification-queries";

type FileSyncSnapshotItem = {
  key: string;
  eventKey: string;
  fileName: string;
  state: string;
};

const PROCESSING_STATES = new Set(["uploading", "uploaded", "queued", "processing", "analyzing"]);
const SYNCED_STATES = new Set(["indexed", "complete", "ready"]);
const NOTIFIED_STORAGE_PREFIX = "violyt:file-sync-notified:";
const MAX_STORED_EVENTS = 300;

function normalizeState(state?: string | null) {
  return String(state || "").trim().toLowerCase();
}

function isProcessingState(state?: string | null) {
  return PROCESSING_STATES.has(normalizeState(state));
}

function isSyncedState(state?: string | null) {
  return SYNCED_STATES.has(normalizeState(state));
}

function getNotifiedStorageKey(userId: string) {
  return `${NOTIFIED_STORAGE_PREFIX}${userId}`;
}

function readNotifiedEvents(userId: string) {
  if (typeof window === "undefined") {
    return new Set<string>();
  }
  try {
    const parsed = JSON.parse(window.localStorage.getItem(getNotifiedStorageKey(userId)) || "[]");
    if (!Array.isArray(parsed)) {
      return new Set<string>();
    }
    return new Set(parsed.map((item) => String(item)).filter(Boolean));
  } catch {
    return new Set<string>();
  }
}

function writeNotifiedEvents(userId: string, events: Set<string>) {
  if (typeof window === "undefined") {
    return;
  }
  const eventList = Array.from(events).slice(-MAX_STORED_EVENTS);
  window.localStorage.setItem(getNotifiedStorageKey(userId), JSON.stringify(eventList));
}

function getAttachmentState(asset: BrandAttachmentResponse) {
  return normalizeState(asset.processing_status?.lifecycle_state || asset.lifecycle_state);
}

function getAttachmentFileName(asset: BrandAttachmentResponse) {
  return asset.original_filename || asset.name || "Uploaded file";
}

function toSnapshotItem(brandId: string, asset: BrandAttachmentResponse): FileSyncSnapshotItem {
  const state = getAttachmentState(asset);
  const key = `${brandId}:${asset.id}`;
  return {
    key,
    eventKey: `${key}:${state}:${asset.updated_at}`,
    fileName: getAttachmentFileName(asset),
    state,
  };
}

async function fetchTenantFileSyncSnapshot(brandIds: string[]) {
  const attachmentResults = await Promise.allSettled(
    brandIds.map(async (brandId) => {
      const groups = await listBrandSpaceAttachments(brandId);
      return groups.flatMap((group) => (group.assets || []).map((asset) => toSnapshotItem(brandId, asset)));
    }),
  );

  return attachmentResults.flatMap((result) => (result.status === "fulfilled" ? result.value : []));
}

export function FileSyncNotifier({ user }: { user: UiUser }) {
  const previousStatesRef = useRef<Map<string, string>>(new Map());
  const hasObservedSnapshotRef = useRef(false);
  const isTenantAdmin = user.role === "TENANT_ADMIN";
  const { data: brands } = useBrands(isTenantAdmin);
  const brandIds = useMemo(
    () =>
      (brands || [])
        .filter((brand) => brand.lifecycle_state !== "deleted" && brand.lifecycle_state !== "archived")
        .map((brand) => brand.id)
        .filter(Boolean),
    [brands],
  );
  const brandIdKey = brandIds.join(",");

  const { data: snapshot = [], isSuccess: hasLoadedSnapshot } = useQuery({
    queryKey: ["brand-space-file-sync-snapshot", user.id, brandIdKey],
    enabled: isTenantAdmin && brandIds.length > 0,
    queryFn: () => fetchTenantFileSyncSnapshot(brandIds),
    refetchInterval: isTenantAdmin && brandIds.length > 0 ? NOTIFICATION_REFETCH_INTERVAL_MS : false,
    refetchOnWindowFocus: false,
  });

  useEffect(() => {
    if (!isTenantAdmin || !hasLoadedSnapshot) {
      return;
    }

    const previousStates = previousStatesRef.current;
    const nextStates = new Map(snapshot.map((item) => [item.key, item.state]));

    if (hasObservedSnapshotRef.current) {
      const notifiedEvents = readNotifiedEvents(user.id);
      let hasNewToast = false;

      snapshot.forEach((item) => {
        const previousState = previousStates.get(item.key);
        const becameSynced =
          isSyncedState(item.state) &&
          ((previousState && isProcessingState(previousState)) || previousState === undefined);

        if (!becameSynced || notifiedEvents.has(item.eventKey)) {
          return;
        }

        toast({
          title: "\uD83C\uDF89 File Ready to Use",
          description: `"${item.fileName}" has finished syncing successfully and is now ready to use.`,
        });

        notifiedEvents.add(item.eventKey);
        hasNewToast = true;
      });

      if (hasNewToast) {
        writeNotifiedEvents(user.id, notifiedEvents);
      }
    }

    previousStatesRef.current = nextStates;
    hasObservedSnapshotRef.current = true;
  }, [hasLoadedSnapshot, isTenantAdmin, snapshot, user.id]);

  return null;
}
