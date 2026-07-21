"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { MoreVertical, Search, X } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { useDeactivateTenantUser, useReactivateTenantUser, useResendTenantUserActivation } from "@/hooks/tenantAdmins/useUpdateTenant";
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
    isActive: boolean;
    isTenantAdmin: boolean;
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

function compactRows(rows: TableRow[]) {
    const seen = new Set<string>();
    return rows.filter((row) => {
        if (seen.has(row.id)) {
            return false;
        }
        seen.add(row.id);
        return true;
    });
}

export default function TeamAccessManager() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const { tenantId, tenantUsers, brandUsers, isLoading } = useTenantUsers();
    const { data: brands } = useBrands();
    const resendActivation = useResendTenantUserActivation(tenantId);
    const deactivateUser = useDeactivateTenantUser(tenantId);
    const reactivateUser = useReactivateTenantUser(tenantId);
    const [activeTab, setActiveTab] = useState<"tenant-users" | "brand-users">("tenant-users");
    const [search, setSearch] = useState("");
    const [createdFilter, setCreatedFilter] = useState<CreatedDateFilter>("all");
    const [activityFilter, setActivityFilter] = useState<"all" | UserActivityStatus>("all");
    const [resendingUserId, setResendingUserId] = useState<string | null>(null);
    const [pendingDeactivateUser, setPendingDeactivateUser] = useState<TableRow | null>(null);
    const activeFilterCount = Number(createdFilter !== "all") + Number(activityFilter !== "all");
    const brandNames = new Map((brands || []).map((brand) => [brand.id, brand.name]));

    const liveTenantRows: TableRow[] = tenantUsers.map((user) => {
        const activityStatus = getUserActivityStatus(user.last_login_at);
        const accountStatus = formatUserAccountStatus(user.is_active, user.is_activated);
        return {
            id: getTenantUserRequestId(user),
            fullName: user.full_name,
            email: user.email,
            createdAt: user.created_at,
            isActive: user.is_active,
            isTenantAdmin: user.role_codes.includes("tenant_admin"),
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
            isActive: user.is_active,
            isTenantAdmin: user.role_codes.includes("tenant_admin"),
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

    const tenantRows = compactRows(liveTenantRows);
    const brandRows = compactRows(liveBrandRows);
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
    const confirmDeactivateUser = async () => {
        if (!pendingDeactivateUser || deactivateUser.isPending) {
            return;
        }

        try {
            await deactivateUser.mutateAsync(pendingDeactivateUser.id);
            setPendingDeactivateUser(null);
        } catch (error) {
            toast({
                title: "Unable to deactivate user",
                description: getApiErrorMessage(error, "Please try again."),
                variant: "destructive",
            });
        }
    };
    const handleReactivateUser = async (row: TableRow) => {
        if (!row.id || reactivateUser.isPending) {
            return;
        }

        try {
            await reactivateUser.mutateAsync(row.id);
        } catch (error) {
            toast({
                title: "Unable to reactivate user",
                description: getApiErrorMessage(error, "Please try again."),
                variant: "destructive",
            });
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
                        <MetricTile label="Super Users" value={String(tenantRows.length)} />
                        <MetricTile label="Brand Users" value={String(brandRows.length)} />
                        {/* <MetricTile label="Brand Assignments" value={String(totalAssignments)} /> */}
                    </div>


                    <div className="w-full flex justify-between border-b py-2">
                    <UserPlatformTabSwitcher
                    className="border-none"
                        tabs={[
                            // { id: "tenant-users", label: `${tenantLabel} Users` },
                            { id: "tenant-users", label: `Super Users` },
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
                        onEditUser={(row) => router.push(`/user_management/${row.id}`)}
                        onDeactivateUser={setPendingDeactivateUser}
                        onReactivateUser={handleReactivateUser}
                    />
                </SectionCard>
                <AlertDialog open={Boolean(pendingDeactivateUser)} onOpenChange={(open) => !open && setPendingDeactivateUser(null)}>
                    <AlertDialogContent className="max-w-[420px] rounded-none border-0 bg-white p-6 shadow-[0_20px_80px_-24px_rgba(15,23,42,0.35)]">
                        <AlertDialogCancel className="absolute right-4 top-4 flex h-6 w-6 items-center justify-center rounded-full border-0 bg-transparent p-0 text-lg leading-none text-slate-500 shadow-none hover:bg-slate-100 hover:text-slate-900 focus-visible:ring-0">
                            <X className="h-4 w-4" />
                            <span className="sr-only">Close</span>
                        </AlertDialogCancel>
                        <AlertDialogHeader>
                            <AlertDialogTitle>Are you sure you want to deactivate this user?</AlertDialogTitle>
                            <AlertDialogDescription>
                                This user will no longer be able to access Violyt until their account is reactivated.
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel className="rounded-none">Cancel</AlertDialogCancel>
                            <AlertDialogAction
                                onClick={(event) => {
                                    event.preventDefault();
                                    void confirmDeactivateUser();
                                }}
                                className="rounded-none bg-[#FF6D5E] text-white hover:bg-[#FF6D5E]/90"
                                disabled={deactivateUser.isPending}
                            >
                                {deactivateUser.isPending ? "Deactivating..." : "Confirm"}
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
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
    onEditUser,
    onDeactivateUser,
    onReactivateUser,
}: {
    headers: string[];
    rows: TableRow[];
    emptyLabel: string;
    resendingUserId: string | null;
    onResendActivation: (row: TableRow) => void;
    onEditUser: (row: TableRow) => void;
    onDeactivateUser: (row: TableRow) => void;
    onReactivateUser: (row: TableRow) => void;
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
                                                <div className="flex items-center justify-between gap-3">
                                                    <div className="flex flex-col items-start gap-1">
                                                        <button
                                                            type="button"
                                                            className="h-7 rounded-none border-none bg-none text-primary font-medium hover:underline cursor-pointer"
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
                                                                        : "Resend Link"}
                                                            </abbr>
                                                        </button>
                                                        {/* Informational text */}
                                                        {/* <span className="text-xs leading-4 text-[#666666]">
                                                            Activation links sent: {row.activationLinkSentCount}
                                                            {row.activationLinkSentCount > 1
                                                                ? ` (resent ${row.activationLinkSentCount - 1} ${row.activationLinkSentCount - 1 === 1 ? "time" : "times"})`
                                                                : ""}
                                                        </span>
                                                        <span className="text-xs leading-4 text-[#666666]">
                                                            Total attempts done: {row.activationLinkSentCount}
                                                        </span> */}
                                                    </div>
                                                    {row.isTenantAdmin ? null : (
                                                        <UserActionMenu
                                                            row={row}
                                                            onEditUser={onEditUser}
                                                            onDeactivateUser={onDeactivateUser}
                                                            onReactivateUser={onReactivateUser}
                                                        />
                                                    )}
                                                </div>
                                            ) : index === 4 ? (
                                                <div className="flex items-center justify-between gap-3">
                                                    <span>{cell}</span>
                                                    {row.isTenantAdmin ? null : (
                                                        <UserActionMenu
                                                            row={row}
                                                            onEditUser={onEditUser}
                                                            onDeactivateUser={onDeactivateUser}
                                                            onReactivateUser={onReactivateUser}
                                                        />
                                                    )}
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

function UserActionMenu({
    row,
    onEditUser,
    onDeactivateUser,
    onReactivateUser,
}: {
    row: TableRow;
    onEditUser: (row: TableRow) => void;
    onDeactivateUser: (row: TableRow) => void;
    onReactivateUser: (row: TableRow) => void;
}) {
    const [open, setOpen] = useState(false);

    const handleEdit = () => {
        setOpen(false);
        onEditUser(row);
    };

    const handleStatusAction = () => {
        setOpen(false);
        if (row.isActive) {
            onDeactivateUser(row);
            return;
        }
        onReactivateUser(row);
    };

    return (
        <DropdownMenu open={open} onOpenChange={setOpen}>
            <DropdownMenuTrigger asChild>
                <button
                    type="button"
                    className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xs text-[#B8B8B8] hover:bg-white hover:text-[#666666]"
                    aria-label={`Open actions for ${row.fullName || row.email}`}
                >
                    <MoreVertical className="h-5 w-5" />
                </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[200px] rounded-none border border-[#EFEFEF] bg-white p-0 shadow-sm">
                <DropdownMenuItem
                    className="rounded-none px-6 py-3 text-base text-[#666666] focus:bg-[#F7F7FB] focus:text-[#2F3342]"
                    onClick={handleEdit}
                >
                    Edit
                </DropdownMenuItem>
                <DropdownMenuItem
                    className="rounded-none border-t border-[#E8E8E8] px-6 py-3 text-base text-[#666666] focus:bg-[#F7F7FB] focus:text-[#2F3342]"
                    onClick={handleStatusAction}
                >
                    {row.isActive ? "Deactivate" : "Reactivate"}
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
}
