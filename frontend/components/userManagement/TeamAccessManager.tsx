"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TableFilterPopover } from "@/components/common/TableFilterPopover";
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
    cells: string[];
    createdAt?: string | null;
    activityStatus: UserActivityStatus;
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
    const { tenantUsers, brandUsers, isLoading } = useTenantUsers();
    const { data: brands } = useBrands();
    const [activeTab, setActiveTab] = useState<"tenant-users" | "brand-users">("tenant-users");
    const [search, setSearch] = useState("");
    const [createdFilter, setCreatedFilter] = useState<CreatedDateFilter>("all");
    const [activityFilter, setActivityFilter] = useState<"all" | UserActivityStatus>("all");
    const activeFilterCount = Number(createdFilter !== "all") + Number(activityFilter !== "all");
    const brandNames = new Map((brands || []).map((brand) => [brand.id, brand.name]));
    const tenantLabel = tenantSummary?.name || "Tenant";

    const liveTenantRows: TableRow[] = tenantUsers.map((user) => {
        const activityStatus = getUserActivityStatus(user.last_login_at);
        return {
            id: getTenantUserRequestId(user),
            createdAt: user.created_at,
            activityStatus,
            cells: [
                user.full_name,
                user.email,
                formatDate(user.created_at),
                formatUserAccountStatus(user.is_active, user.is_activated),
                formatUserActivityStatus(activityStatus),
            ],
        };
    });

    const liveBrandRows: TableRow[] = brandUsers.map((user) => {
        const brandAssignmentLabel =
            user.brand_space_ids.map((brandId) => brandNames.get(brandId) || brandId).join(", ") || "-";
        const activityStatus = getUserActivityStatus(user.last_login_at);
        return {
            id: getTenantUserRequestId(user),
            createdAt: user.created_at,
            activityStatus,
            cells: [
                user.full_name,
                user.email,
                formatDate(user.created_at),
                formatUserAccountStatus(user.is_active, user.is_activated),
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
    const totalAssignments = brandRows.reduce((sum, row) => {
        const assignments = row.cells[5];
        if (!assignments || assignments === "-") {
            return sum;
        }
        return sum + assignments.split(",").filter(Boolean).length;
    }, 0);

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
}: {
    headers: string[];
    rows: TableRow[];
    emptyLabel: string;
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
