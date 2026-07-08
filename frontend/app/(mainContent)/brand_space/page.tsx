"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
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
import BrandSpaces from "@/components/brandSpaces/BrandSpaces";
import {
    PlatformPageTitle,
    SearchField,
    SectionCard,
    UserPlatformTabSwitcher,
} from "@/components/platformOwner/PlatformOwnerPrimitives";
import { toast } from "@/components/ui/use-toast";
import { useArchiveBrandMutation, useBrands, useDeleteBrandMutation, usePublishBrandMutation, useRestoreBrandMutation, useUnpublishBrandMutation } from "@/hooks/useBrands";
import { useRBAC } from "@/hooks/useRBAC";
import type { BrandResponse } from "@/lib/api/contracts";
import { clearBrandSpaceDraft } from "@/lib/brand-space-persistence";
import Image from "next/image";
import { request } from "@/lib/api/request";
import { API } from "@/lib/api/endpoints";
import { mapBrandOverviewToForm } from "@/lib/brand-mappers";
import {
    formatMissingRequiredBrandFields,
    getMissingRequiredBrandFields,
} from "@/lib/brand-space-validation";
import { buildBrandEditHref } from "@/lib/brand-routing";

function getBrandId(item: BrandResponse | { id: string }) {
    return item.id;
}

function getBrandDisplayName(item: BrandResponse | { name?: string; slug?: string; lifecycle_state?: string }) {
    const lifecycleLabel =
        item.lifecycle_state === "draft"
            ? "Draft"
            : item.lifecycle_state === "active"
                ? "Active"
                : item.lifecycle_state === "archived"
                    ? "Archived"
                    : "";
    return item.name?.trim() || item.slug?.trim() || lifecycleLabel || "Brand Space";
}

export default function BrandSpacePage() {
    const router = useRouter();
    const { user, can } = useRBAC();
    const { data: brands, isLoading } = useBrands();
    const publishBrand = usePublishBrandMutation();
    const unpublishBrand = useUnpublishBrandMutation();
    const archiveBrand = useArchiveBrandMutation();
    const restoreBrand = useRestoreBrandMutation();
    const deleteBrand = useDeleteBrandMutation();
    const isAdmin = user?.role === "TENANT_ADMIN";
    const [activeTab, setActiveTab] = useState<"brand_spaces" | "archive">("brand_spaces");
    const [searchQuery, setSearchQuery] = useState("");
    const [pendingDeleteBrand, setPendingDeleteBrand] = useState<{ id: string; name: string } | null>(null);

    const liveActiveSpaces = useMemo(
        () => (brands || []).filter((brand) => brand.lifecycle_state !== "archived" && brand.lifecycle_state !== "deleted"),
        [brands],
    );
    const liveArchivedSpaces = useMemo(
        () => (brands || []).filter((brand) => brand.lifecycle_state === "archived"),
        [brands],
    );
    const activeSpaces = liveActiveSpaces;
    const archivedSpaces = liveArchivedSpaces;
    const visibleSpaces = activeTab === "brand_spaces" ? activeSpaces : archivedSpaces;
    const filteredVisibleSpaces = useMemo(() => {
        const query = searchQuery.trim().toLowerCase();
        if (!query) {
            return visibleSpaces;
        }

        return visibleSpaces.filter((brand) =>
            [
                brand.name,
                brand.slug,
                brand.lifecycle_state,
            ]
                .filter(Boolean)
                .some((value) => String(value).toLowerCase().includes(query)),
        );
    }, [searchQuery, visibleSpaces]);

    const runBrandAction = async (
        action: () => Promise<unknown>,
        successMessage: string,
        failureMessage: string,
    ) => {
        try {
            await action();
            toast({
                title: successMessage,
                variant: "success",
            });
        } catch (error) {
            const description = error instanceof Error ? error.message : failureMessage;
            toast({
                title: failureMessage,
                description,
                variant: "destructive",
            });
        }
    };

    const publishBrandSpace = async (item: BrandResponse) => {
        try {
            const overview = await request(API.BRANDS.OVERVIEW, { pathParams: item.id });
            const missingRequiredFields = getMissingRequiredBrandFields(mapBrandOverviewToForm(overview));

            if (missingRequiredFields.length) {
                toast({
                    title: "Complete required fields before publishing",
                    description: `Please complete: ${formatMissingRequiredBrandFields(missingRequiredFields)}.`,
                    variant: "warning",
                });
                router.push(buildBrandEditHref(item));
                return;
            }

            await publishBrand.mutateAsync(getBrandId(item));
            toast({
                title: "Brand Space activated",
                variant: "success",
            });
        } catch (error) {
            const description = error instanceof Error ? error.message : "Unable to activate this Brand Space right now.";
            toast({
                title: "Unable to activate this Brand Space right now.",
                description,
                variant: "destructive",
            });
        }
    };

    const confirmDeleteBrandSpace = () => {
        if (!pendingDeleteBrand || deleteBrand.isPending) {
            return;
        }
        const brand = pendingDeleteBrand;
        setPendingDeleteBrand(null);
        void runBrandAction(
            () => deleteBrand.mutateAsync(brand.id),
            "Brand Space deleted",
            "Unable to delete this Brand Space right now.",
        );
    };

    return (
        <div className="w-full px-4 py-6">
            <div className="space-y-6">
                <PlatformPageTitle
                    title="Brand Spaces"
                    action={
                        <div className="flex gap-4">
                            {isAdmin && (
                                <Button
                                    onClick={() => router.push("/brand_space/usage")}
                                    variant="outline"
                                    className="w-33 h-12 rounded-none border border-primary bg-white px-5 text-[15px] font-semibold text-primary hover:bg-[#F7F7FB]"
                                >
                                    <span>Edit Usage</span>
                                </Button>
                            )}
                            {can("BRAND_SPACE", "CREATE") && (
                                <Button
                                    onClick={() => {
                                        clearBrandSpaceDraft();
                                        router.push("/brand_space/new?fresh=1");
                                    }}
                                    className="flex w-52 h-12 items-center justify-center gap-2 rounded-none border-0 bg-primary/72 px-5 text-[15px] font-semibold hover:bg-primary/90"
                                >
                                    <Image src="/actions_icons/add.svg" alt="plus icon" width={16} height={16} />
                                    <span>New Brand Space</span>
                                </Button>
                            )}
                        </div>
                    }
                >
                </PlatformPageTitle>

                <div className="flex items-center justify-between gap-4">
                    <UserPlatformTabSwitcher
                        tabs={[
                            { id: "brand_spaces", label: "Your Space" },
                            { id: "archive", label: "Archive" },
                        ]}
                        active={activeTab}
                        onChange={(tab) => setActiveTab(tab as "brand_spaces" | "archive")}
                    />
                    <SearchField value={searchQuery} onChange={setSearchQuery} />
                </div>
            </div>
                <SectionCard className="border-none p-0" >
                    {isLoading ? (
                        <div className="py-10 text-sm text-slate-500">Loading brand spaces...</div>
                    ) : visibleSpaces.length === 0 ? (
                        <div className="w-full mx-auto flex items-center justify-center py-10 text-sm text-slate-500">
                            {activeTab === "brand_spaces"
                                ? "No Brand Spaces yet. Start by creating a new Brand Space."
                                : "No archived Brand Spaces yet."}
                        </div>
                    ) : filteredVisibleSpaces.length === 0 ? (
                        <div className="w-full mx-auto flex items-center justify-center py-10 text-sm text-slate-500">
                            No Brand Spaces match your search.
                        </div>
                    ) : (
                        <BrandSpaces
                            items={filteredVisibleSpaces}
                            onPublish={(item) => {
                                void publishBrandSpace(item);
                            }}
                            onUnpublish={(item) => {
                                void runBrandAction(
                                    () => unpublishBrand.mutateAsync(getBrandId(item)),
                                    "Brand Space moved to draft",
                                    "Unable to move this Brand Space to draft right now.",
                                );
                            }}
                            onArchive={(item) => {
                                void runBrandAction(
                                    () => archiveBrand.mutateAsync(getBrandId(item)),
                                    "Brand Space archived",
                                    "Unable to archive this Brand Space right now.",
                                );
                            }}
                            onRestore={(item) => {
                                void runBrandAction(
                                    () => restoreBrand.mutateAsync(getBrandId(item)),
                                    "Brand Space restored",
                                    "Unable to restore this Brand Space right now.",
                                );
                            }}
                            onDelete={(item) => {
                                setPendingDeleteBrand({
                                    id: getBrandId(item),
                                    name: getBrandDisplayName(item),
                                });
                            }}
                        />
                    )}
                </SectionCard>
                <AlertDialog open={Boolean(pendingDeleteBrand)} onOpenChange={(open) => !open && setPendingDeleteBrand(null)}>
                    <AlertDialogContent className="max-w-[420px] rounded-none border-0 bg-white p-6 shadow-[0_20px_80px_-24px_rgba(15,23,42,0.35)]">
                        <AlertDialogHeader>
                            <AlertDialogTitle>Delete Brand Space?</AlertDialogTitle>
                            <AlertDialogDescription>
                                Are you sure you want to delete &quot;{pendingDeleteBrand?.name || "Brand Space"}&quot;?
                            </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                            <AlertDialogCancel className="rounded-none">Cancel</AlertDialogCancel>
                            <AlertDialogAction
                                onClick={(event) => {
                                    event.preventDefault();
                                    confirmDeleteBrandSpace();
                                }}
                                className="rounded-none bg-[#FF6D5E] text-white hover:bg-[#FF6D5E]/90"
                                disabled={deleteBrand.isPending}
                            >
                                {deleteBrand.isPending ? "Deleting..." : "Delete"}
                            </AlertDialogAction>
                        </AlertDialogFooter>
                    </AlertDialogContent>
                </AlertDialog>
        </div>
    );
}
