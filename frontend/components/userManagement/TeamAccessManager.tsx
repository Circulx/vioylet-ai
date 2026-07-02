"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TableFilterPopover } from "@/components/common/TableFilterPopover";
import { toast } from "@/components/ui/use-toast";
import {
    MetricTile,
    PlatformPageTitle,
    SectionCard,
    UserPlatformTabSwitcher,
} from "@/components/platformOwner/PlatformOwnerPrimitives";
import { getTenantUserRequestId, useTenantUsers } from "@/hooks/useTeamAccess";
import { useBrands } from "@/hooks/useBrands";
import { useGetMe } from "@/hooks/useUser";
import { useGetTenantData } from "@/hooks/tenantAdmins/useGetTenants";
import { useResendTenantUserActivation } from "@/hooks/tenantAdmins/useUpdateTenant";
import { getApiErrorMessage } from "@/lib/api/error-message";
import {
    CREATED_DATE_FILTER_OPTIONS,
    USER_ACTIVITY_FILTER_OPTIONS,
    type CreatedDateFilter,
    type UserActivityStatus,
    matchesCreatedDateFilter,
    getUserActivityStatus,
    formatUserActivityStatus,
    formatUserAccountStatus,
} from "@/lib/table-filters";
import Image from "next/image";

function formatDate(value?: string | null) {
    if (!value) {
        return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleDateString("en-GB");
}

type TableRow = {
    id: string;
    fullName: string;
    email: string;
    cells: string[];
    createdAt?: string | null;
    activityStatus: UserActivityStatus;
    isPendingActivation: boolean;
    activationLinkSentCount: number;
    activationLinkAttemptsLeft: number;
};

function matchesSearch(row: TableRow, search: string) {
    if (!search.trim()) {
        return true;
    }
    const query = search.trim().toLowerCase();
    return row.cells.slice(0, 2).some((cell) => cell.toLowerCase().includes(query));
}

export default function TeamAccessManager() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { data: currentUser } = useGetMe();
    const { data: tenantSummary } = useGetTenantData(currentUser?.tenantId ?? "");
    const { tenantId, tenantUsers, brandUsers, isLoading } = useTenantUsers();
    const { data: brands } = useBrands();
    const resendActivation = useResendTenantUserActivation(tenantId);
    const [activeTab, setActiveTab] = useState<"tenant-users" | "brand-users">("tenant-users");
    const [search, setSearch] = useState("");
    const [createdFilter, setCreatedFilter] = useState<CreatedDateFilter>("all");
    const [activityFilter, setActivityFilter] = useState<"all" | UserActivityStatus>("all");
    const [resendingUserId, setResendingUserId] = useState<string | null>(null);
    const activeFilterCount = Number(createdFilter !== "all") + Number(activityFilter !== "all");
    const brandNames = new Map((brands || []).map((brand) => [brand.id, brand.name]));
    const tenantLabel = tenantSummary?.name || "Tenant";

    const liveTenantRows: TableRow[] = tenantUsers.map((user) => {
        const activityStatus = getUserActivityStatus(user.last_login_at);
        const accountStatus = formatUserAccountStatus(user.is_active, user.is_activated);
        return {
            id: getTenantUserRequestId(user),
            fullName: user.full_name,
            email: user.email,
            createdAt: user.created_at,
            activityStatus,
            isPendingActivation: user.is_active && !user.is_activated,
            activationLinkSentCount: user.activation_link_sent_count || 0,
            activationLinkAttemptsLeft: user.activation_link_attempts_left || 0,
            cells: [
                user.full_name,
                user.email,
                formatDate(user.created_at),
                accountStatus,
                formatUserActivityStatus(activityStatus),
            ],
        };
    });

    const liveBrandRows: TableRow[] = brandUsers.map((user) => {
        const brandAssignmentLabel =
            user.brand_space_ids.map((brandId) => brandNames.get(brandId) || brandId).join(", ") || "-";
        const activityStatus = getUserActivityStatus(user.last_login_at);
        const accountStatus = formatUserAccountStatus(user.is_active, user.is_activated);
        return {
            id: getTenantUserRequestId(user),
            fullName: user.full_name,
            email: user.email,
            createdAt: user.created_at,
            activityStatus,
            isPendingActivation: user.is_active && !user.is_activated,
            activationLinkSentCount: user.activation_link_sent_count || 0,
            activationLinkAttemptsLeft: user.activation_link_attempts_left || 0,
            cells: [
                user.full_name,
                user.email,
                formatDate(user.created_at),
                accountStatus,
                formatUserActivityStatus(activityStatus),
                brandAssignmentLabel,
                // user.last_login_at ? formatDate(user.last_login_at) : "Recent",
            ],
        };
    });

    const tenantRows = liveTenantRows;
    const brandRows = liveBrandRows;
    const visibleRows = (activeTab === "tenant-users" ? tenantRows : brandRows).filter((row) => {
        return (
            matchesSearch(row, search) &&
            matchesCreatedDateFilter(row.createdAt, createdFilter) &&
            (activityFilter === "all" || row.activityStatus === activityFilter)
        );
    });
    const creationFeedback = useMemo(() => {
        if (searchParams.get("created") !== "1") {
            return null;
        }
        const email = searchParams.get("email") || "the new user";
        const status = searchParams.get("emailStatus");
        const reason = searchParams.get("emailReason");
        if (status === "sent") {
            return {
                tone: "success" as const,
                title: "User created successfully",
                description: `Activation email sent to ${email}.`,
            };
        }
        return {
            tone: "warning" as const,
            title: "User created, but activation email was not sent",
            description: reason ? `${email}: ${reason}` : `${email}: Email delivery could not be completed.`,
        };
    }, [searchParams]);
    const handleResendActivation = async (row: TableRow) => {
        if (!row.id || resendActivation.isPending) {
            return;
        }

        setResendingUserId(row.id);
        try {
            const delivery = await resendActivation.mutateAsync(row.id);
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
        } catch (error) {
            toast({
                title: "Unable to resend activation link",
                description: getApiErrorMessage(error, "Please try again."),
                variant: "destructive",
            });
        } finally {
            setResendingUserId(null);
        }
    };

    return (
        <div className="container">
            <div>
                <PlatformPageTitle
                    title="Team Access"
                    action={
                        <Button asChild className="h-12 rounded-none bg-primary/72 px-5 text-[15px] font-medium hover:bg-primary/90">
                            <Link href="/user_management/create">
                                <Image src="/actions_icons/add.svg" alt="plus icon" width={16} height={16} />
                                <span className="font-semibold">Invite User</span>
                            </Link>
                        </Button>
                    }
                >
                    <div className="grid gap-4 md:grid-cols-2">
                        <MetricTile label="Tenant Users" value={String(tenantRows.length)} />
                        <MetricTile label="Brand Users" value={String(brandRows.length)} />
                        {/* <MetricTile label="Brand Assignments" value={String(totalAssignments)} /> */}
                    </div>


                    <div className="w-full flex justify-between border-b py-2">
                    <UserPlatformTabSwitcher
                    className="border-none"
                        tabs={[
                            { id: "tenant-users", label: `${tenantLabel} Users` },
                            { id: "brand-users", label: "Brand Users" },
                        ]}
                        active={activeTab}
                        onChange={(tab) => setActiveTab(tab as "tenant-users" | "brand-users")}
                    />
                    <div className="flex flex-wrap items-center justify-between gap-4 pb-2">
                        <div className="flex flex-wrap items-center gap-3">
                            <UserSearchField
                                value={search}
                                onChange={setSearch}
                            />
                            <TableFilterPopover
                                createdLabel="Date Created"
                                createdValue={createdFilter}
                                createdOptions={CREATED_DATE_FILTER_OPTIONS}
                                onCreatedChange={setCreatedFilter}
                                activityLabel="Active Last 30 Days"
                                activityValue={activityFilter}
                                activityOptions={USER_ACTIVITY_FILTER_OPTIONS}
                                onActivityChange={setActivityFilter}
                                onClear={() => {
                                    setCreatedFilter("all");
                                    setActivityFilter("all");
                                }}
                                activeFilterCount={activeFilterCount}
                                buttonAriaLabel="Open user filters"
                            />
                        </div>
                    </div>
                    </div>
                </PlatformPageTitle>
                {creationFeedback ? (
                    <Alert
                        className={
                            creationFeedback.tone === "success"
                                ? "border-[#CFE6D6] bg-[#F4FBF6] text-[#1F6B38]"
                                : "border-[#F1D9A7] bg-[#FFF8EA] text-[#8A5A00]"
                        }
                    >
                        <AlertTitle className="text-inherit">{creationFeedback.title}</AlertTitle>
                        <AlertDescription className="text-inherit/90">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                                <p>{creationFeedback.description}</p>
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="h-9 rounded-[10px] border-current/25 bg-transparent px-3 text-current hover:bg-white/70"
                                    onClick={() => router.replace("/user_management")}
                                >
                                    Dismiss
                                </Button>
                            </div>
                        </AlertDescription>
                    </Alert>
                ) : null}

                <SectionCard className="border-none shadow-none p-0">
                    <UserTable
                        emptyLabel={isLoading ? "Loading users..." : "No matching users found"}
                        headers={
                            activeTab === "tenant-users"
                                ? ["Name", "Email ID", "Date Created", "Status", "Active Last 30 Days"]
                                : ["Name", "Email ID", "Date Created", "Status", "Active Last 30 Days", "Brand Space"]
                        }
                        rows={visibleRows}
                        resendingUserId={resendingUserId}
                        onResendActivation={handleResendActivation}
                    />
                </SectionCard>
            </div>
        </div>
    );
}

function UserSearchField({
    value,
    onChange,
}: {
    value: string;
    onChange: (value: string) => void;
}) {
    return (
        <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#A1A1AA]" />
            <Input
                value={value}
                onChange={(event) => onChange(event.target.value)}
                placeholder="Search users"
                className="h-10 w-[250px] rounded-none border-[#E5E7EB] bg-white pl-9 pr-4"
            />
        </div>
    );
}

function UserTable({
    headers,
    rows,
    emptyLabel,
    resendingUserId,
    onResendActivation,
}: {
    headers: string[];
    rows: TableRow[];
    emptyLabel: string;
    resendingUserId: string | null;
    onResendActivation: (row: TableRow) => void;
}) {
    return (
        <div className="overflow-hidden rounded-xs">
            <div className="overflow-x-auto">
                <table className="table">
                    <thead className="border-b border-[#ECEEF5]">
                        <tr className="min-w-full bg-slate-100/50 text-black">
                            {headers.map((header) => (
                                <th key={header} className="w-1/7 border-2 border-white px-4 py-3 font-medium text-black">
                                    {header}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.length ? (
                            rows.map((row) => (
                                <tr
                                    key={row.id}
                                    className="min-w-full bg-slate-100/50 text-[#666666]"
                                >
                                    {row.cells.map((cell, index) => (
                                        <td key={`${row.id}-${index}`} className="w-1/7 border-2 border-white px-4 py-3">
                                            {index === 0 ? (
                                                <Link href={`/user_management/${row.id}`} className="font-medium text-[#2F3342] hover:text-primary">
                                                    {cell}
                                                </Link>
                                            ) : index === 4 && row.isPendingActivation ? (
                                                <div className="flex flex-col items-start gap-1">
                                                    <Button
                                                        type="button"
                                                        variant="outline"
                                                        size="xs"
                                                        className="h-7 rounded-none border-primary/30 px-2 text-primary hover:bg-primary/10"
                                                        disabled={resendingUserId === row.id || row.activationLinkAttemptsLeft <= 0}
                                                        onClick={() => onResendActivation(row)}
                                                        title="Resend Activation Link"
                                                        aria-label={`Resend Activation Link to ${row.fullName || row.email}`}
                                                    >
                                                        <abbr title="Resend Activation Link" className="no-underline">
                                                            {resendingUserId === row.id
                                                                ? "Sending..."
                                                                : row.activationLinkAttemptsLeft <= 0
                                                                    ? "Limit reached"
                                                                    : "Resend"}
                                                        </abbr>
                                                    </Button>
                                                    <span className="text-xs leading-4 text-[#666666]">
                                                        Activation links sent: {row.activationLinkSentCount}
                                                        {row.activationLinkSentCount > 1
                                                            ? ` (resent ${row.activationLinkSentCount - 1} ${row.activationLinkSentCount - 1 === 1 ? "time" : "times"})`
                                                            : ""}
                                                    </span>
                                                    <span className="text-xs leading-4 text-[#666666]">
                                                        Total attempts done: {row.activationLinkSentCount}
                                                    </span>
                                                </div>
                                            ) : (
                                                cell
                                            )}
                                        </td>
                                    ))}
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td className="px-4 py-6 text-sm text-slate-500" colSpan={headers.length}>
                                    {emptyLabel}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
