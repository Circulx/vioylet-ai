"use client";

import { useMemo, useState, type MouseEvent } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { TableFilterPopover } from "@/components/common/TableFilterPopover";
import { toast } from "@/components/ui/use-toast";
import { PlatformPageTitle, Pager, SearchField } from "@/components/platformOwner/PlatformOwnerPrimitives";
import { useGetTenants } from "@/hooks/tenantAdmins/useGetTenants";
import { useResendTenantUserActivation } from "@/hooks/tenantAdmins/useUpdateTenant";
import { getApiErrorMessage } from "@/lib/api/error-message";
import { formatShortDate, formatTenantDisplayName, getActivityLabel } from "@/lib/platform-owner";
import {
    CREATED_DATE_FILTER_OPTIONS,
    RECENT_ACTIVITY_FILTER_OPTIONS,
    type CreatedDateFilter,
    type RecentActivityFilter,
    getRecentActivityStatus,
    matchesCreatedDateFilter,
} from "@/lib/table-filters";
import Image from "next/image";

const PAGE_SIZE_OPTIONS = [10, 25, 50];

export default function TenantManagementPage() {
    const router = useRouter();
    const { data, isLoading, error } = useGetTenants();
    const resendActivation = useResendTenantUserActivation("");
    const [search, setSearch] = useState("");
    const [createdFilter, setCreatedFilter] = useState<CreatedDateFilter>("all");
    const [activityFilter, setActivityFilter] = useState<RecentActivityFilter>("all");
    const [pageSize, setPageSize] = useState(10);
    const [page, setPage] = useState(1);
    const [resendingAdminId, setResendingAdminId] = useState<string | null>(null);
    const activeFilterCount = Number(createdFilter !== "all") + Number(activityFilter !== "all");

    const items = useMemo(() => {
        const source = data || [];
        const query = search.toLowerCase();
        return source.filter((tenant) => {
            const matchesQuery =
                !search.trim() ||
                [tenant.name, formatTenantDisplayName(tenant.name), tenant.tenant_admin_name, tenant.contact_email].some((value) =>
                    value?.toLowerCase().includes(query),
                );
            const matchesCreated = matchesCreatedDateFilter(tenant.created_at, createdFilter);
            const matchesActivity =
                activityFilter === "all" || getRecentActivityStatus(tenant.last_active_at) === activityFilter;

            return matchesQuery && matchesCreated && matchesActivity;
        });
    }, [activityFilter, createdFilter, data, search]);

    const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
    const currentPage = Math.min(page, totalPages);
    const startIndex = (currentPage - 1) * pageSize;
    const pageItems = items.slice(startIndex, startIndex + pageSize);

    const handleResendActivation = async (
        event: MouseEvent<HTMLButtonElement>,
        tenantId: string,
        adminUserId?: string | null,
    ) => {
        event.stopPropagation();
        if (!tenantId || !adminUserId || resendActivation.isPending) {
            return;
        }

        setResendingAdminId(adminUserId);
        try {
            const delivery = await resendActivation.mutateAsync({ tenantId, userId: adminUserId });
            if (delivery.delivered) {
                toast({
                    title: "Activation link resent",
                    description: `Activation link sent to ${delivery.recipient_email}.`,
                });
            } else {
                toast({
                    title: "Activation email was not sent",
                    description: delivery.reason || `${delivery.recipient_email}: Email delivery could not be completed.`,
                    variant: "destructive",
                });
            }
        } catch (resendError) {
            toast({
                title: "Unable to resend activation link",
                description: getApiErrorMessage(resendError, "Please try again."),
                variant: "destructive",
            });
        } finally {
            setResendingAdminId(null);
        }
    };

    if (isLoading) {
        return <div className="p-5 text-sm text-slate-500">Loading tenants...</div>;
    }

    if (error) {
        return <div className="p-5 text-sm text-red-500">Unable to load tenants.</div>;
    }

    return (
        <div className="w-full px-4 py-6">
            <div className="space-y-8">
                <PlatformPageTitle
                    title="Tenant Management"
                    action={
                        <Button
                            onClick={() => router.push("/tenants/create")}
                            className="flex h-12 items-center gap-2 rounded-xs bg-primary/72 px-5 text-base font-semibold hover:bg-primary/90"
                        >
                            <Image src={"/actions_icons/add.svg"} alt="Add" width={16} height={16} className="w-5.5 h-5.5" />
                            {/* <PlusCircle fill="white" className="text-primary/72 h-6 w-6" /> */}
                            New Tenant
                        </Button>
                    }
                />

                <div className="flex items-center justify-between gap-4">
                    <h2 className="text-xl font-semibold tracking-tight text-[#2F3342]">Tenant Accounts</h2>
                    <div className="flex flex-wrap gap-1">
                        <SearchField value={search} onChange={(value) => {
                            setSearch(value);
                            setPage(1);
                        }} />
                        <TableFilterPopover
                            createdLabel="Date Created"
                            createdValue={createdFilter}
                            createdOptions={CREATED_DATE_FILTER_OPTIONS}
                            onCreatedChange={(value) => {
                                setCreatedFilter(value);
                                setPage(1);
                            }}
                            activityLabel="Active Last 30 Days"
                            activityValue={activityFilter}
                            activityOptions={RECENT_ACTIVITY_FILTER_OPTIONS}
                            onActivityChange={(value) => {
                                setActivityFilter(value);
                                setPage(1);
                            }}
                            onClear={() => {
                                setCreatedFilter("all");
                                setActivityFilter("all");
                                setPage(1);
                            }}
                            activeFilterCount={activeFilterCount}
                            buttonAriaLabel="Open tenant filters"
                        />
                    </div>
                </div>

                <div className="flex max-h-[calc(100vh-17rem)] min-h-0 flex-col overflow-hidden rounded-[2px] border border-[#ECEEF5] bg-white shadow-[0_10px_24px_-22px_rgba(15,23,42,0.45)]">
                    <div className="min-h-0 flex-1 overflow-auto">
                        <table className="table">
                            <thead className="bg-[#F6F7FC] text-[#4B5563]">
                                <tr>
                                    <th className="w-1/6 px-4 py-4 font-bold text-black">Tenant Name</th>
                                    <th className="w-1/6 px-4 py-4 font-bold text-black">Date Created</th>
                                    <th className="w-1/6 px-4 py-4 font-bold text-black">Tenant Admin</th>
                                    <th className="w-1/6 px-4 py-4 font-bold text-black">Brand Spaces</th>
                                    <th className="w-1/6 px-4 py-4 font-bold text-black">Status</th>
                                    <th className="w-1/6 px-4 py-4 font-bold text-black">Active (Last 30 Days)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {pageItems.length ? (
                                    pageItems.map((tenant) => {
                                        const isPendingActivation =
                                            tenant.tenant_admin_is_active !== false &&
                                            tenant.tenant_admin_is_activated === false;
                                        const adminStatus = tenant.tenant_admin_user_id
                                            ? isPendingActivation
                                                ? "Pending"
                                                : tenant.tenant_admin_is_active === false
                                                    ? "Inactive"
                                                    : "Active"
                                            : "-";
                                        const attemptsLeft = tenant.tenant_admin_activation_link_attempts_left ?? 0;
                                        return (
                                            <tr
                                                key={tenant.id}
                                                className="cursor-pointer border-b border-[#F1F2F6] text-[#4B5563] hover:bg-[#FAFAFD]"
                                                onClick={() => router.push(`/tenants/${tenant.id}`)}
                                            >
                                                <td className="px-4 py-3">{formatTenantDisplayName(tenant.name)}</td>
                                                <td className="px-4 py-3">{formatShortDate(tenant.created_at)}</td>
                                                <td className="px-4 py-3">{tenant.tenant_admin_name || "-"}</td>
                                                <td className="px-4 py-3">{tenant.brand_space_count}</td>
                                                <td className="px-4 py-3">{adminStatus}</td>
                                                <td className="px-4 py-3">
                                                    {isPendingActivation ? (
                                                        <button
                                                            type="button"
                                                            className="font-medium text-primary hover:underline disabled:cursor-not-allowed disabled:text-[#9CA3AF] disabled:no-underline"
                                                            disabled={
                                                                resendingAdminId === tenant.tenant_admin_user_id ||
                                                                attemptsLeft <= 0 ||
                                                                !tenant.tenant_admin_user_id
                                                            }
                                                            onClick={(event) =>
                                                                handleResendActivation(
                                                                    event,
                                                                    tenant.id,
                                                                    tenant.tenant_admin_user_id,
                                                                )
                                                            }
                                                            title="Resend Activation Link"
                                                            aria-label={`Resend Activation Link to ${tenant.tenant_admin_name || tenant.tenant_admin_email || tenant.name}`}
                                                        >
                                                            <abbr title="Resend Activation Link" className="no-underline">
                                                                {resendingAdminId === tenant.tenant_admin_user_id
                                                                    ? "Sending..."
                                                                    : attemptsLeft <= 0
                                                                        ? "Limit reached"
                                                                        : "Resend Link"}
                                                            </abbr>
                                                        </button>
                                                    ) : (
                                                        getActivityLabel(tenant.last_active_at)
                                                    )}
                                                </td>
                                            </tr>
                                        );
                                    })
                                ) : (
                                    <tr>
                                        <td colSpan={6} className="px-4 py-8 text-center text-[#6B7280]">
                                            No tenants match the selected filters
                                        </td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                </div>

                <div className="absolute bottom-0 left-0 right-0 z-10 flex items-center justify-between gap-4 overflow-x-auto bg-white px-4 py-3 text-sm text-[#4B5563]">
                    <div className="flex shrink-0 items-center gap-3">
                        <span>Show</span>
                        <select
                            className="h-9 rounded-[8px] border border-[#D5D8E8] bg-white px-3"
                            value={pageSize}
                            onChange={(event) => {
                                setPageSize(Number(event.target.value));
                                setPage(1);
                            }}
                        >
                            {PAGE_SIZE_OPTIONS.map((option) => (
                                <option key={option} value={option}>
                                    {option}
                                </option>
                            ))}
                        </select>
                        <span>Entries</span>
                    </div>
                    <div className="shrink-0">
                        <Pager
                            page={currentPage}
                            totalPages={totalPages}
                            onPrevious={() => setPage((value) => Math.max(1, value - 1))}
                            onNext={() => setPage((value) => Math.min(totalPages, value + 1))}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
