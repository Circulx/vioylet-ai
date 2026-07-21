"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  MetricTile,
  PlatformPageTitle,
  SectionCard,
} from "@/components/platformOwner/PlatformOwnerPrimitives";
import { useBrands } from "@/hooks/useBrands";
import { useGetMe } from "@/hooks/useUser";
import { useGetTenantData, useGetTenantUsers } from "@/hooks/tenantAdmins/useGetTenants";
import { useUpdateBrandUsageTargets } from "@/hooks/tenantAdmins/useUpdateTenant";
import { addInAppNotificationForRecipients } from "@/hooks/useInAppNotifications";

type UsageRow = {
  id: string;
  name: string;
  value: number;
};

export default function BrandUsageAllocationPage() {
  const { data: currentUser } = useGetMe();
  const tenantId = currentUser?.tenantId ?? "";
  const { data: tenant } = useGetTenantData(tenantId);
  const { data: tenantUsers } = useGetTenantUsers(currentUser?.role === "TENANT_ADMIN" ? tenantId : "");
  const { data: brands } = useBrands();
  const updateBrandUsageTargets = useUpdateBrandUsageTargets();

  const initialRows = useMemo<UsageRow[]>(() => {
    const configuredTargets = (tenant?.metadata_json?.brand_usage_targets as Record<string, number> | undefined) ?? {};
    const activeBrands = (brands || []).filter((brand) => brand.lifecycle_state !== "archived" && brand.lifecycle_state !== "deleted");
    if (!activeBrands.length) {
      return [];
    }
    const evenSplit = Math.floor(100 / activeBrands.length);
    return activeBrands.map((brand, index) => ({
      id: brand.id,
      name: brand.name,
      value:
        typeof configuredTargets[brand.id] === "number"
          ? configuredTargets[brand.id]
          : index === activeBrands.length - 1
            ? 100 - evenSplit * (activeBrands.length - 1)
            : evenSplit,
    }));
  }, [brands, tenant?.metadata_json?.brand_usage_targets]);

  const [rows, setRows] = useState<UsageRow[]>(initialRows);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const isSavingRef = useRef(false);

  useEffect(() => {
    setRows(initialRows);
  }, [initialRows]);

  const total = rows.reduce((sum, row) => sum + row.value, 0);
  const savedAllocationKey = useMemo(
    () => JSON.stringify(initialRows.map((row) => [row.id, row.value]).sort()),
    [initialRows],
  );
  const currentAllocationKey = useMemo(
    () => JSON.stringify(rows.map((row) => [row.id, row.value]).sort()),
    [rows],
  );
  const hasChanges = rows.length > 0 && currentAllocationKey !== savedAllocationKey;
  const notificationRecipientIds = useMemo(() => {
    const recipients = new Set<string>();
    if (
      currentUser?.tenantId === tenantId &&
      (currentUser?.role === "TENANT_ADMIN" || currentUser?.role === "TENANT_USER")
    ) {
      recipients.add(currentUser.id);
    }
    for (const user of tenantUsers || []) {
      if (!user.is_active || user.tenant_id !== tenantId) {
        continue;
      }
      if (user.role_codes.includes("tenant_admin") || user.role_codes.includes("tenant_user")) {
        recipients.add(user.id);
      }
    }
    return Array.from(recipients);
  }, [currentUser?.id, currentUser?.role, currentUser?.tenantId, tenantId, tenantUsers]);

  const notifyCapacityUsageUpdated = (brandUsageTargets: Record<string, number>) => {
    if (!(currentUser?.role === "TENANT_ADMIN" || currentUser?.role === "TENANT_USER")) {
      return;
    }
    const totalAllocation = Object.values(brandUsageTargets).reduce((sum, value) => sum + Number(value || 0), 0);
    addInAppNotificationForRecipients(notificationRecipientIds, {
      title: "Capacity Usage Updated",
      message: `Brand capacity allocations have been updated. The total allocation is now ${totalAllocation}%. Review the latest allocations in Capacity Usage.`,
    });
  };

  return (
    <div className="container">
      <div className="mx-auto space-y-6">
        <PlatformPageTitle
          title="Edit Capacity Usage"
          action={
            <Button
              className="h-12 rounded-none bg-primary/72 px-6 text-[15px] font-medium hover:bg-primary/90"
              disabled={updateBrandUsageTargets.isPending || !hasChanges}
              onClick={() => {
                if (isSavingRef.current || updateBrandUsageTargets.isPending || !hasChanges) {
                  return;
                }
                if (!tenantId || !tenant) {
                  setError("Tenant context is missing.");
                  return;
                }
                if (total > 100) {
                  setError("Brand usage allocation cannot be more than 100% before saving.");
                  return;
                }
                setError(null);
                setFeedback(null);
                isSavingRef.current = true;
                updateBrandUsageTargets.mutate(
                  {
                    id: tenantId,
                    brandUsageTargets: Object.fromEntries(rows.map((row) => [row.id, row.value])),
                  },
                  {
                    onSuccess: (response) => {
                      setFeedback("Usage allocation saved successfully.");
                      notifyCapacityUsageUpdated(response.brand_usage_targets);
                    },
                    onError: () => setError("Unable to save usage allocation right now."),
                    onSettled: () => {
                      isSavingRef.current = false;
                    },
                  },
                );
              }}
            >
              {updateBrandUsageTargets.isPending ? "Saving..." : "Save"}
            </Button>
          }
        />

        <div className="grid gap-4 md:grid-cols-3">
          <MetricTile label="Assigned Brands" value={String(rows.length)} />
          <MetricTile label="Current Total" value={`${total}%`} />
          <MetricTile label="Status" value={total === 100 ? "Balanced" : "Under allocated"} />
        </div>

        <SectionCard title="Usage Overview" className="border-none p-0">
          <div className="space-y-1">
            <p className="text-sm text-[#6B7280] mb-6">
              This does not restrict usage. It helps track usage and triggers alerts as the limit approaches.
            </p>
            {feedback ? <p className="text-sm text-emerald-600">{feedback}</p> : null}
            {error ? <p className="text-sm text-red-500">{error}</p> : null}
          </div>

          <div className="max-w-[685px] space-y-2">
            <div className="grid grid-cols-2 gap-2 text-base font-semibold text-[#121212]">
              <div className="rounded-[4px] bg-[#F5F6FA] px-3 py-3.5">Brand</div>
              <div className="rounded-[4px] bg-[#F5F6FA] px-3 py-3.5">Usage</div>
            </div>
            {rows.map((row) => (
              <div key={row.id} className="grid grid-cols-2 gap-2">
                <div className="rounded-[4px] bg-[#F5F6FA] px-3 py-3.5 text-base font-normal text-[#121212]">{row.name}</div>
                <input
                  aria-label={`${row.name} usage allocation`}
                  inputMode="numeric"
                  value={`${row.value}%`}
                  onChange={(event) => {
                    const numericValue = Number(event.target.value.replace(/[^\d]/g, "") || 0);
                    const nextValue = Math.max(0, Math.min(100, numericValue));
                    setFeedback(null);
                    setError(null);
                    setRows((current) => current.map((item) => (item.id === row.id ? { ...item, value: nextValue } : item)));
                  }}
                  className="min-w-0 rounded-[4px] bg-[#F5F6FA] px-3 py-3.5 text-base font-medium text-[#121212] outline-none transition focus:ring-2 focus:ring-primary/20"
                />
              </div>
            ))}
          </div>

          <p className="text-sm text-[#6B7280] mt-6">Current total allocation: {total}%</p>
        </SectionCard>
      </div>
    </div>
  );
}
