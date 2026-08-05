"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
    AlertCircle,
    CheckCircle2,
    Clock3,
    Eye,
    FileText,
    Loader2,
    RefreshCw,
    Sparkles,
    Unplug,
} from "lucide-react";
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
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Collapsible,
    CollapsibleContent,
} from "@/components/ui/collapsible";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeading } from "@/components/common/DesignPrimitives";
import { InformationTip } from "@/components/InformationTip";
import { BrandSpaceHistoryDrawer } from "@/components/brandSpaces/BrandSpaceHistoryDrawer";
import type { BrandAttachmentResponse, BrandResponse, ValidationSummaryResponse } from "@/lib/api/contracts";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";
import { buildBrandWorkspaceHref } from "@/lib/brand-routing";
import { brandSpaceTabs } from "@/lib/brandSpace";
import {
    formatMissingRequiredBrandFields,
    getBrandTabCompletion,
    getMissingRequiredBrandFields,
} from "@/lib/brand-space-validation";
import {
    clearBrandSpaceDraft,
    emptyUploadedBrandAssets,
    listBrandSpaceAttachments,
    loadBrandSpaceDraft,
    mergeBrandAttachmentsIntoForm,
    saveBrandSpaceDraft,
    syncBrandSpaceAssetStatuses,
    uploadBrandSpaceAssets,
    type UploadedBrandAssets,
} from "@/lib/brand-space-persistence";
import { mapBrandFormToCreateRequest, mapBrandSections } from "@/lib/brand-mappers";
import { cn } from "@/lib/utils";
import { useAutofillBrandFromKnowledge, useBrands, useCreateBrand } from "@/hooks/useBrands";
import { applyBrandAutofillToForm } from "@/lib/brand-autofill";
import { useGetMe } from "@/hooks/useUser";
import { useGetTenantData } from "@/hooks/tenantAdmins/useGetTenants";
import { useUpdateBrandUsageTargets } from "@/hooks/tenantAdmins/useUpdateTenant";
import { toast } from "@/components/ui/use-toast";
import {
    emptyBrandFormState,
    findBrandUploadItem,
    normalizeBrandLogoItems,
    removeBrandUploadItem,
    updateBrandUploadItemState,
    type BrandUploadItem,
    type BrandFormState,
} from "@/types/brand-space.types";

type BrandSpaceEditorProps = {
    mode: "create" | "edit" | "view";
    brandId?: string;
    initialForm?: BrandFormState;
    initialLifecycleState?: string;
    skipDraftHydration?: boolean;
};

const STATUS_POLL_INTERVAL_MS = 4000;
const NEW_BRAND_CAPACITY_ROW_ID = "__new_brand__";
const ATTACHMENT_TAB_VALUES = new Set([
    "core_brand_signals",
    "target_audience",
    "visual_identity",
    "brand_rules",
    "brand_knowledge",
]);

type UploadStatusItem = {
    id: string;
    uploadedAssetId?: string;
    name: string;
    section: string;
    lifecycleState?: string;
    pageCount?: number;
    processingError?: string | null;
    validationState?: string;
};

type CapacityUsageRow = {
    id: string;
    name: string;
    value: number;
    isCurrentBrand?: boolean;
    isNewBrand?: boolean;
};

type BrandSubmitIntent = "draft" | "publish" | "save" | "unpublish";

function normalizeUploadState(state?: string) {
    const normalized = (state || "").toLowerCase();
    return normalized || "selected";
}

function getUploadStateLabel(state?: string) {
    const normalized = normalizeUploadState(state);
    if (normalized === "selected") return "Ready";
    if (normalized === "uploading") return "Uploading";
    if (normalized === "uploaded" || normalized === "queued") return "Queued";
    if (normalized === "analyzing") return "Analyzing";
    if (normalized === "processing") return "Processing";
    if (["indexed", "complete", "ready"].includes(normalized)) return "Synced";
    if (normalized === "failed") return "Failed";
    if (normalized === "deleted") return "Deleted";
    return state || "Ready";
}

function collectUploadStatusItems(form: BrandFormState): UploadStatusItem[] {
    const items: UploadStatusItem[] = [];
    const pushItems = (section: string, uploads: BrandUploadItem[]) => {
        uploads.forEach((item) => {
            items.push({
                id: item.id,
                uploadedAssetId: item.uploadedAssetId,
                name: item.name,
                section,
                lifecycleState: item.lifecycleState,
                pageCount: item.pageCount,
                processingError: item.processingError,
                validationState: item.validationState,
            });
        });
    };

    pushItems("Core Brand Signals", form.core.logos.length ? form.core.logos : form.core.logo ? [form.core.logo] : []);
    pushItems("Target Audience", form.targetAudience.audienceInsights);
    pushItems("Visual Identity", form.visualIdentity.referenceCreatives);
    pushItems("Visual Identity", form.visualIdentity.moodBoards);
    pushItems("Visual Identity", form.visualIdentity.colorPaletteUploads);
    pushItems("Visual Identity", form.visualIdentity.uploadedFonts);
    pushItems("Visual Identity", form.visualIdentity.fontStyleGuide);
    pushItems("Brand Rules", form.brandRules.positiveWordBankUploads);
    pushItems("Brand Rules", form.brandRules.replaceableWordUploads);
    pushItems("Brand Rules", form.brandRules.negativeWordBankUploads);
    pushItems("Brand Knowledge", form.brandKnowledge.templateFiles);
    pushItems("Brand Knowledge", form.brandKnowledge.otherDocuments);

    return items;
}

type UploadStatePatch = Parameters<typeof updateBrandUploadItemState>[2];

function toRecord(value: unknown): Record<string, unknown> {
    return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function extractedHex(entry: Record<string, unknown>) {
    return String(entry.hex_code || entry.hex || "").trim();
}

function extractedRole(entry: Record<string, unknown>) {
    return String(entry.role || "").trim().toLowerCase();
}

function colorPaletteEntriesFromData(data: Record<string, unknown>) {
    const structuredEntries = Array.isArray(data.palette_entries)
        ? data.palette_entries
        : Array.isArray(data.palette)
            ? data.palette
            : Array.isArray(data.all)
                ? data.all
                : [];
    const seenHexes = new Set<string>();
    return structuredEntries
        .map(toRecord)
        .filter((entry) => {
            const hex = extractedHex(entry).toUpperCase();
            if (!hex || seenHexes.has(hex)) {
                return false;
            }
            seenHexes.add(hex);
            return true;
        });
}

function colorPaletteEntriesFromUploadItem(item: BrandUploadItem | null | undefined) {
    if (!item) {
        return [];
    }
    return [
        ...colorPaletteEntriesFromData(item.structuredDataJson || {}),
        ...colorPaletteEntriesFromData(item.normalizedDataJson || {}),
    ].filter((entry, index, entries) => {
        const hex = extractedHex(entry).toUpperCase();
        return hex && entries.findIndex((candidate) => extractedHex(candidate).toUpperCase() === hex) === index;
    });
}

function colorNameFromPaletteEntry(entry: Record<string, unknown>) {
    return String(
        entry.color_name ||
        entry.name ||
        extractedRole(entry) ||
        "Additional color",
    );
}

function applyColorPaletteEntries(
    form: BrandFormState,
    activeColorPaletteUploadId: string,
    entries: Record<string, unknown>[],
): BrandFormState {
    const primary = entries.find((entry) => extractedRole(entry) === "primary") || entries[0];
    const secondary = entries.find((entry) => extractedRole(entry) === "secondary") || entries[1];
    const additional = entries.filter((entry) => ![primary, secondary].includes(entry));
    return {
        ...form,
        visualIdentity: {
            ...form.visualIdentity,
            activeColorPaletteUploadId,
            primaryColor: primary ? extractedHex(primary) : "",
            secondaryColor: secondary ? extractedHex(secondary) : "",
            additionalColors: additional.length
                ? additional.map((entry) => ({
                    name: colorNameFromPaletteEntry(entry),
                    hex: extractedHex(entry),
                }))
                : [{ name: "", hex: "" }],
        },
    };
}

function selectColorPaletteUpload(form: BrandFormState, itemId: string): BrandFormState {
    const selectedItem = form.visualIdentity.colorPaletteUploads.find((item) => item.id === itemId);
    if (!selectedItem) {
        return form;
    }
    const entries = colorPaletteEntriesFromUploadItem(selectedItem);
    if (!entries.length) {
        return {
            ...form,
            visualIdentity: {
                ...form.visualIdentity,
                activeColorPaletteUploadId: itemId,
            },
        };
    }
    return applyColorPaletteEntries(form, itemId, entries);
}

function attachmentToUploadPatch(asset: BrandAttachmentResponse): UploadStatePatch {
    return {
        uploadedAssetId: asset.id,
        assetUrl: asset.asset_url || undefined,
        storagePath: asset.storage_path,
        lifecycleState: asset.processing_status?.lifecycle_state || asset.lifecycle_state,
        channel: asset.channel,
        mimeType: asset.mime_type,
        pageCount: asset.page_count,
        processingError: asset.processing_error,
        fieldKey: asset.field_key || undefined,
        assetCategory: asset.asset_category || undefined,
        validationState: asset.validation_state,
        validationSummaryJson: asset.validation_summary_json,
        structuredDataJson: asset.structured_data_json,
        normalizedDataJson: asset.normalized_data_json,
        processingStatus: asset.processing_status || undefined,
        routing: asset.routing || undefined,
        isActive: asset.is_active,
    };
}

function syncActiveColorPaletteFields(form: BrandFormState): BrandFormState {
    const activeId = form.visualIdentity.activeColorPaletteUploadId;
    if (activeId) {
        return selectColorPaletteUpload(form, activeId);
    }
    const firstProcessedItem = form.visualIdentity.colorPaletteUploads.find(
        (item) => colorPaletteEntriesFromUploadItem(item).length > 0,
    );
    if (firstProcessedItem) {
        return selectColorPaletteUpload(form, firstProcessedItem.id);
    }
    return form.visualIdentity.colorPaletteUploads.length
        ? form
        : {
            ...form,
            visualIdentity: {
                ...form.visualIdentity,
                activeColorPaletteUploadId: "",
            },
        };
}

function isSyncedUploadPatch(patch: UploadStatePatch) {
    const state = normalizeUploadState(
        patch.lifecycleState || patch.processingStatus?.lifecycle_state,
    );
    return ["indexed", "complete", "ready"].includes(state);
}

function applyExtractedVisualIdentityData(
    form: BrandFormState,
    patch: UploadStatePatch,
    itemId?: string,
): BrandFormState {
    if (!isSyncedUploadPatch(patch)) {
        return form;
    }

    const fieldKey = String(patch.fieldKey || "").trim();
    const assetCategory = String(patch.assetCategory || "").trim();
    const structuredData = patch.structuredDataJson || {};
    let visualIdentity = form.visualIdentity;
    let changed = false;

    if (fieldKey === "color_palette" || assetCategory === "color_palette") {
        const entries = colorPaletteEntriesFromData(structuredData);
        const activeId = form.visualIdentity.activeColorPaletteUploadId;
        if (entries.length && itemId && (!activeId || activeId === itemId)) {
            return applyColorPaletteEntries(form, itemId, entries);
        }
    }

    if (fieldKey === "font_guide" || assetCategory === "typography_guide") {
        const fontFamilies = Array.isArray(structuredData.font_families)
            ? structuredData.font_families.map(toRecord)
            : [];
        const usagePatterns = toRecord(structuredData.usage_patterns);
        const typographyText = [
            ...fontFamilies.map((font) => String(font.name || "").trim()),
            String(usagePatterns.heading || "").trim(),
            String(usagePatterns.body || "").trim(),
        ]
            .filter(Boolean)
            .filter((value, index, values) => values.indexOf(value) === index)
            .join(", ");

        if (!visualIdentity.typography && typographyText) {
            visualIdentity = {
                ...visualIdentity,
                typography: typographyText,
            };
            changed = true;
        }
    }

    return changed ? { ...form, visualIdentity } : form;
}

function FileProcessingStatusTipContent() {
    return (
        <div className="space-y-2 text-left">
            <p className="font-medium text-[#6F6F6F]">File Processing Status</p>
            <p>These statuses indicate the current state of files uploaded to this Brand Space.</p>
            <div className="space-y-1">
                <p><span className="font-medium text-[#6F6F6F]">Ready:</span> Files have been uploaded successfully and are waiting to be processed.</p>
                <p><span className="font-medium text-[#6F6F6F]">Processing:</span> Files are currently being processed. During this stage, Violyt extracts and analyzes the content to make it available for use.</p>
                <p><span className="font-medium text-[#6F6F6F]">Synced:</span> File processing has been completed successfully, and the content is fully synchronized with the Brand Space. These files are now available for content generation and other Brand Space features.</p>
            </div>
        </div>
    );
}
function UploadStatusPanel({
    items,
    isSubmitting,
    actionItemId,
    onReprocess,
    onUnsync,
    onRemove,
}: {
    items: UploadStatusItem[];
    isSubmitting: boolean;
    actionItemId: string | null;
    onReprocess: (itemId: string) => void | Promise<void>;
    onUnsync: (itemId: string) => void | Promise<void>;
    onRemove: (itemId: string) => void | Promise<void>;
}) {
    const [isOpen, setIsOpen] = useState(false);
    if (!items.length) {
        return null;
    }

    const counts = items.reduce(
        (summary, item) => {
            const normalized = normalizeUploadState(item.lifecycleState);
            if (normalized === "failed") {
                summary.failed += 1;
            } else if (["indexed", "complete", "ready"].includes(normalized)) {
                summary.synced += 1;
            } else if (["uploading", "uploaded", "queued", "processing", "analyzing"].includes(normalized)) {
                summary.processing += 1;
            } else {
                summary.ready += 1;
            }
            return summary;
        },
        { ready: 0, processing: 0, synced: 0, failed: 0 },
    );

    return (
        <div className="rounded-2xl border border-[#E3E6F2] bg-white px-5 py-4 my-6 shadow-[0_14px_32px_-28px_rgba(15,23,42,0.65)]">
            <Collapsible
                open={isOpen}
                onOpenChange={setIsOpen}
            >
                <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                        <h2 className="text-base font-semibold text-slate-800">File Processing</h2>
                        <p className="mt-1 text-sm text-slate-500">
                            {isSubmitting
                                ? "Uploads, OCR, and template analysis are running in the background. Larger files can take a few minutes."
                                : "Attached files stay linked to this Brand Space. You can reprocess, unsync, or remove them here."}
                        </p>
                    </div>
                    <div className="flex flex-wrap items-center justify-end gap-2 text-xs font-medium">
                        <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">{counts.ready} Ready</span>
                        <span className="rounded-full bg-primary/10 px-3 py-1 text-primary">{counts.processing} Processing</span>
                        <span className="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">{counts.synced} Synced</span>
                        {counts.failed ? (
                            <span className="rounded-full bg-red-50 px-3 py-1 text-red-600">{counts.failed} Failed</span>
                        ) : null}
                        <button
                            type="button"
                            onClick={() => setIsOpen((current) => !current)}
                            className="ml-1 text-xs font-medium text-primary hover:underline"
                        >
                            {isOpen ? "View less" : "View more"}
                        </button>
                        <InformationTip content={<FileProcessingStatusTipContent />} />
                    </div>
                </div>
                <CollapsibleContent className="flex flex-col gap-2">

            <div className="mt-4 max-h-105 space-y-2 overflow-auto pr-1">
                {items.map((item) => {
                    const normalized = normalizeUploadState(item.lifecycleState);
                    const label = getUploadStateLabel(item.lifecycleState);
                    const isReadyToUpload = normalized === "selected";
                    const isQueued = ["uploaded", "queued"].includes(normalized);
                    const isProcessing = ["uploading", "processing", "analyzing"].includes(normalized);
                    const isReady = ["indexed", "complete", "ready"].includes(normalized);
                    const isFailed = normalized === "failed";
                    const isActioning = actionItemId === item.id;

                    return (
                        <div
                            key={item.id}
                            className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/70 px-3 py-3"
                        >
                            <div className="min-w-0 flex-1">
                                <p className="truncate text-sm font-medium text-slate-700">{item.name}</p>
                                <p className="mt-1 text-xs text-slate-500">{item.section}</p>
                                {item.validationState && item.validationState !== "pending" ? (
                                    <p className="mt-1 text-xs text-slate-500">Validation: {item.validationState}</p>
                                ) : null}
                                {item.processingError ? <p className="mt-1 text-xs text-red-500">{item.processingError}</p> : null}
                                {item.pageCount ? (
                                    <p className="mt-1 text-xs text-slate-500">
                                        {item.pageCount} OCR page{item.pageCount > 1 ? "s" : ""}
                                    </p>
                                ) : null}
                            </div>

                            <div className="flex min-w-47.5 flex-col items-end gap-2">
                                <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                                    {isReadyToUpload ? <FileText className="h-3.5 w-3.5 text-slate-500" /> : null}
                                    {isProcessing ? <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" /> : null}
                                    {isQueued ? <Loader2 className="h-3.5 w-3.5 text-amber-500" /> : null}
                                    {isReady ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> : null}
                                    {isFailed ? <AlertCircle className="h-3.5 w-3.5 text-red-500" /> : null}
                                    <span
                                        className={
                                            isFailed
                                                ? "text-red-500"
                                                : isReady
                                                    ? "text-emerald-700"
                                                    : isProcessing
                                                        ? "text-primary"
                                                        : isQueued
                                                            ? "text-amber-600"
                                                            : "text-slate-500"
                                        }
                                    >
                                        {label}
                                    </span>
                                </div>

                                <div className="flex flex-wrap justify-end gap-2">
                                    {item.uploadedAssetId ? (
                                        <>
                                            <button
                                                type="button"
                                                onClick={() => void onReprocess(item.id)}
                                                disabled={isActioning}
                                                className="inline-flex items-center gap-1 text-xs font-medium text-primary disabled:opacity-50"
                                            >
                                                <RefreshCw className="h-3.5 w-3.5" />
                                                Reprocess
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => void onUnsync(item.id)}
                                                disabled={isActioning}
                                                className="inline-flex items-center gap-1 text-xs font-medium text-amber-700 disabled:opacity-50"
                                            >
                                                <Unplug className="h-3.5 w-3.5" />
                                                Unsync
                                            </button>
                                        </>
                                    ) : null}
                                    <button
                                        type="button"
                                        onClick={() => void onRemove(item.id)}
                                        disabled={isActioning}
                                        className="text-xs font-medium text-red-600 disabled:opacity-50"
                                    >
                                        Remove
                                    </button>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
                </CollapsibleContent>


            </Collapsible>


        </div>
    );
}

function ValidationSummaryPanel({
    lifecycleState,
    summary,
}: {
    lifecycleState: string;
    summary: ValidationSummaryResponse | null;
}) {
    const warnings = summary?.warnings || [];
    const conflicts = summary?.conflicts || [];
    const excludedAssets = summary?.excluded_assets || [];
    const validationResults = summary?.validation_results || [];
    const trustSummary = validationResults.reduce(
        (acc, item) => {
            const trustLevel = item.trust_level || "reference_only";
            if (trustLevel === "trusted") {
                acc.trusted += 1;
            } else if (trustLevel === "usable_with_warning") {
                acc.warning += 1;
            } else if (trustLevel === "excluded") {
                acc.excluded += 1;
            } else {
                acc.reference += 1;
            }
            return acc;
        },
        { trusted: 0, warning: 0, reference: 0, excluded: 0 },
    );

    return (
        <div className="rounded-none border border-[#E3E6F2] bg-white px-5 py-4 shadow-[0_14px_32px_-28px_rgba(15,23,42,0.65)]">
            {/* <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-slate-800">Lifecycle & Validation</h2>
          <p className="mt-1 text-sm text-slate-500">
            Draft Brand Spaces can keep syncing files in the background. Generation opens only after the Brand Space is active.
          </p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${
            lifecycleState === "active"
              ? "bg-emerald-50 text-emerald-700"
              : "bg-amber-50 text-amber-700"
          }`}
        >
          {lifecycleState || "draft"}
        </span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Warnings</p>
          <p className="mt-2 text-2xl font-semibold text-slate-800">{warnings.length}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Conflicts</p>
          <p className="mt-2 text-2xl font-semibold text-slate-800">{conflicts.length}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Excluded Assets</p>
          <p className="mt-2 text-2xl font-semibold text-slate-800">{excludedAssets.length}</p>
        </div>
      </div>

      {warnings.length ? (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {warnings.slice(0, 3).map((warning, index) => (
            <p key={`${warning}-${index}`}>{warning}</p>
          ))}
        </div>
      ) : (
        <div className="mt-4 rounded-sm border border-primary/20 bg-primary/22 px-4 py-3 text-sm text-primary">
          Validated data is synced and ready to inform generation.
        </div>
      )}

      {conflicts.length ? (
        <div className="mt-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {conflicts.slice(0, 2).map((conflict) => (
            <p key={conflict.id}>
              {conflict.conflict_type} ({conflict.severity})
            </p>
          ))}
        </div>
      ) : null}

      {validationResults.length ? (
        <div className="mt-3 grid gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-emerald-700">Trusted</p>
            <p className="mt-2 text-xl font-semibold text-emerald-800">{trustSummary.trusted}</p>
          </div>
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-amber-700">Usable With Warning</p>
            <p className="mt-2 text-xl font-semibold text-amber-800">{trustSummary.warning}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Reference Only</p>
            <p className="mt-2 text-xl font-semibold text-slate-800">{trustSummary.reference}</p>
          </div>
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
            <p className="text-xs uppercase tracking-[0.18em] text-red-700">Excluded</p>
            <p className="mt-2 text-xl font-semibold text-red-800">{trustSummary.excluded}</p>
          </div>
        </div>
      ) : null} */}
        </div>
    );
}

function hasPendingBackgroundProcessing(uploads: UploadedBrandAssets) {
    const assets = [
        ...uploads.logos,
        ...uploads.audienceInsights,
        ...uploads.referenceCreatives,
        ...uploads.moodBoards,
        ...uploads.colorPaletteUploads,
        ...uploads.uploadedFonts,
        ...uploads.fontStyleGuide,
        ...uploads.positiveWordBankUploads,
        ...uploads.replaceableWordUploads,
        ...uploads.negativeWordBankUploads,
        ...uploads.templateFiles,
        ...uploads.otherDocuments,
    ];

    return assets.some((asset) => {
        const state = normalizeUploadState(asset.processing_status?.lifecycle_state || asset.lifecycle_state);
        return !["indexed", "ready", "complete", "failed", "deleted"].includes(state);
    });
}

function clampCapacityValue(value: number) {
    if (!Number.isFinite(value)) {
        return 0;
    }
    return Math.max(0, Math.min(Math.round(value), 100));
}

function parseCapacityValue(value: string) {
    return clampCapacityValue(Number(value.replace(/[^\d]/g, "") || 0));
}

export default function BrandSpaceEditor({
    mode,
    brandId,
    initialForm = emptyBrandFormState,
    initialLifecycleState = "draft",
    skipDraftHydration = false,
}: BrandSpaceEditorProps) {
    const router = useRouter();

    const queryClient = useQueryClient();
    const createBrand = useCreateBrand();
    const updateBrandUsageTargets = useUpdateBrandUsageTargets();
    const { data: currentUser } = useGetMe();
    const tenantId = currentUser?.tenantId ?? "";
    const { data: tenant } = useGetTenantData(tenantId);
    const { data: brands } = useBrands();
    const isReadOnly = mode === "view";

    const [form, setForm] = useState<BrandFormState>(initialForm);
    const [submissionPhase, setSubmissionPhase] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [activeSubmitIntent, setActiveSubmitIntent] = useState<BrandSubmitIntent | null>(null);
    const [draftBrand, setDraftBrand] = useState<BrandResponse | null>(null);
    const [draftBrandId, setDraftBrandId] = useState<string | null>(brandId ?? null);
    const autofillFromKnowledge = useAutofillBrandFromKnowledge(draftBrandId || brandId || "");
    const [brandLifecycleState, setBrandLifecycleState] = useState(initialLifecycleState);
    const [validationSummary, setValidationSummary] = useState<ValidationSummaryResponse | null>(null);
    const [didHydrateDraft, setDidHydrateDraft] = useState(mode !== "create");
    const [actionItemId, setActionItemId] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState(brandSpaceTabs[0].value);
    const [hydratedBrandStateId, setHydratedBrandStateId] = useState<string | null>(null);
    const [hydratedAttachmentBrandId, setHydratedAttachmentBrandId] = useState<string | null>(null);
    const [capacityDialogOpen, setCapacityDialogOpen] = useState(false);
    const [editConfirmationOpen, setEditConfirmationOpen] = useState(false);
    const [capacityRows, setCapacityRows] = useState<CapacityUsageRow[]>([]);
    const [capacityError, setCapacityError] = useState<string | null>(null);
    const formRef = useRef(form);
    const readOnlySetForm = useMemo(() => (() => undefined) as typeof setForm, []);

    useEffect(() => {
        formRef.current = form;
    }, [form]);

    useEffect(() => {
        if (mode !== "edit" && mode !== "view") {
            return;
        }
        const nextLogos = normalizeBrandLogoItems(
            initialForm.core.logos.length
                ? initialForm.core.logos
                : initialForm.core.logo
                    ? [initialForm.core.logo]
                    : [],
        );
        setForm({
            ...initialForm,
            core: {
                ...initialForm.core,
                logos: nextLogos,
                logo: nextLogos[0] || initialForm.core.logo || null,
            },
        });
        setDraftBrandId(brandId ?? null);
        setBrandLifecycleState(initialLifecycleState);
        setHydratedBrandStateId(null);
        setHydratedAttachmentBrandId(null);
    }, [brandId, initialForm, initialLifecycleState, mode]);

    useEffect(() => {
        if (mode !== "create") {
            return;
        }
        if (skipDraftHydration) {
            clearBrandSpaceDraft();
            setForm(structuredClone(emptyBrandFormState));
            setDraftBrand(null);
            setDraftBrandId(null);
            setBrandLifecycleState("draft");
            setValidationSummary(null);
            setHydratedBrandStateId(null);
            setHydratedAttachmentBrandId(null);
            setDidHydrateDraft(true);
            return;
        }
        const draft = loadBrandSpaceDraft();
        if (draft) {
            const nextLogos = normalizeBrandLogoItems(
                draft.form.core.logos.length
                    ? draft.form.core.logos
                    : draft.form.core.logo
                        ? [draft.form.core.logo]
                        : [],
            );
            setForm({
                ...draft.form,
                core: {
                    ...draft.form.core,
                    logos: nextLogos,
                    logo: nextLogos[0] || draft.form.core.logo || null,
                },
            });
            setDraftBrandId(draft.brandId || null);
            setBrandLifecycleState(draft.lifecycleState || "draft");
        }
        setDidHydrateDraft(true);
    }, [mode, skipDraftHydration]);

    useEffect(() => {
        if (isReadOnly || mode !== "create" || !didHydrateDraft) {
            return;
        }
        saveBrandSpaceDraft({
            brandId: draftBrandId,
            lifecycleState: brandLifecycleState,
            form,
        });
    }, [brandLifecycleState, didHydrateDraft, draftBrandId, form, isReadOnly, mode]);

    const effectiveBrandId = draftBrandId ?? brandId ?? null;
    const activeTabNeedsAttachments = ATTACHMENT_TAB_VALUES.has(activeTab);

    const handleTabChange = (nextTab: string) => {
        setActiveTab(nextTab);
    };

    useEffect(() => {
        if (!effectiveBrandId || hydratedBrandStateId === effectiveBrandId) {
            return;
        }

        let isCancelled = false;

        const hydrateBrandState = async () => {
            try {
                const [brand, validation] = await Promise.all([
                    request(API.BRANDS.DETAIL, { pathParams: effectiveBrandId }),
                    request(API.BRANDS.VALIDATION, { pathParams: effectiveBrandId }),
                ]);
                if (isCancelled) {
                    return;
                }
                setDraftBrand(brand);
                setBrandLifecycleState(brand.lifecycle_state);
                setValidationSummary(validation);
                setHydratedBrandStateId(effectiveBrandId);
            } catch {
                // Keep current local state if hydration fails.
            }
        };

        void hydrateBrandState();

        return () => {
            isCancelled = true;
        };
    }, [effectiveBrandId, hydratedBrandStateId]);

    useEffect(() => {
        if (!effectiveBrandId || !activeTabNeedsAttachments || hydratedAttachmentBrandId === effectiveBrandId) {
            return;
        }

        let isCancelled = false;

        const hydrateAttachments = async () => {
            try {
                const attachments = await listBrandSpaceAttachments(effectiveBrandId);
                if (isCancelled) {
                    return;
                }
                setForm((current) => {
                    const merged = syncActiveColorPaletteFields(mergeBrandAttachmentsIntoForm(current, attachments));
                    formRef.current = merged;
                    return merged;
                });
                setHydratedAttachmentBrandId(effectiveBrandId);
            } catch {
                // Keep current local state if hydration fails.
            }
        };

        void hydrateAttachments();

        return () => {
            isCancelled = true;
        };
    }, [activeTabNeedsAttachments, effectiveBrandId, hydratedAttachmentBrandId]);

    const tabCompletion = useMemo(
        () => getBrandTabCompletion(form, brandSpaceTabs.map((tab) => tab.value)),
        [form],
    );
    const uploadStatusItems = useMemo(() => collectUploadStatusItems(form), [form]);
    const hasPendingUploadItems = useMemo(
        () =>
            uploadStatusItems.some((item) =>
                ["uploading", "uploaded", "queued", "processing", "analyzing"].includes(
                    normalizeUploadState(item.lifecycleState),
                ),
            ),
        [uploadStatusItems],
    );
    const hasUnsavedUploadItems = useMemo(
        () => uploadStatusItems.some((item) => normalizeUploadState(item.lifecycleState) === "selected"),
        [uploadStatusItems],
    );
    const canOpenWorkspace = Boolean(effectiveBrandId) && brandLifecycleState === "active";
    const canShowHistoryButton =
        Boolean(effectiveBrandId) &&
        brandLifecycleState === "active" &&
        currentUser?.role !== "PLATFORM_OWNER";
    const primarySubmitIntent: "publish" | "save" =
        brandLifecycleState === "active" || hasUnsavedUploadItems ? "save" : "publish";
    const isDraftSubmitting = isSubmitting && activeSubmitIntent === "draft";
    const isUnpublishSubmitting = isSubmitting && activeSubmitIntent === "unpublish";
    const isPrimarySubmitting =
        isSubmitting && (activeSubmitIntent === "publish" || activeSubmitIntent === "save");
    const capacityTotal = capacityRows.reduce((sum, row) => sum + row.value, 0);
    const currentBrandCapacityRow = capacityRows.find((row) => row.isCurrentBrand || row.isNewBrand);
    const requiresPublishedEditConfirmation =
        mode === "edit" && brandLifecycleState === "active" && primarySubmitIntent === "save";

    const showSuccessToast = (title: string, description?: string) => {
        toast({
            title,
            description,
            variant: "success",
        });
    };

    const showInfoToast = (title: string, description?: string) => {
        toast({
            title,
            description,
            variant: "info",
        });
    };

    const showWarningToast = (title: string, description?: string) => {
        toast({
            title,
            description,
            variant: "warning",
        });
    };

    const showErrorToast = (title: string, description?: string) => {
        toast({
            title,
            description,
            variant: "destructive",
        });
    };

    const validateRequiredFieldsForPublish = () => {
        const missingRequiredFields = getMissingRequiredBrandFields(formRef.current);
        if (!missingRequiredFields.length) {
            return true;
        }

        const message = `Please complete: ${formatMissingRequiredBrandFields(missingRequiredFields)}.`;
        setActiveTab(missingRequiredFields[0].tab);
        showWarningToast("Complete required fields before publishing", message);
        return false;
    };

    const handleAutofillFromKnowledge = async () => {
        const effectiveId = draftBrandId || brandId;
        if (!effectiveId) {
            showWarningToast(
                "Save a draft first",
                "Create/save the Brand Space draft, upload documents, then auto-fill from knowledge.",
            );
            return;
        }
        try {
            setSubmissionPhase("Reading vector knowledge...");
            const suggestion = await autofillFromKnowledge.mutateAsync();
            setForm((current) => {
                const merged = applyBrandAutofillToForm(current, suggestion);
                formRef.current = merged;
                return merged;
            });
            const remaining = getMissingRequiredBrandFields(formRef.current);
            const note = suggestion.notes?.join(" ") || "";
            if (remaining.length) {
                showWarningToast(
                    "Auto-filled from knowledge",
                    `${note} Still needed: ${formatMissingRequiredBrandFields(remaining)}.`,
                );
                setActiveTab(remaining[0].tab);
            } else {
                showSuccessToast(
                    "Auto-filled from knowledge",
                    note || "Publish-required fields were filled from the vector DB.",
                );
            }
        } catch (error) {
            const message = axios.isAxiosError(error)
                ? String(error.response?.data?.detail || error.message)
                : error instanceof Error
                    ? error.message
                    : "Autofill failed";
            showErrorToast("Could not auto-fill", message);
        } finally {
            setSubmissionPhase(null);
        }
    };

    const buildCapacityRows = () => {
        const configuredTargets = (tenant?.metadata_json?.brand_usage_targets as Record<string, number> | undefined) ?? {};
        const activeBrands = (brands || []).filter((brand) => {
            return brand.lifecycle_state !== "archived" && brand.lifecycle_state !== "deleted";
        });
        const shouldIncludeNewBrand = mode === "create" && !effectiveBrandId;
        const configuredTotalExcludingCurrent = activeBrands.reduce((sum, brand) => {
            if (effectiveBrandId && brand.id === effectiveBrandId) {
                return sum;
            }
            const value = configuredTargets[brand.id];
            return sum + (typeof value === "number" ? clampCapacityValue(value) : 0);
        }, 0);

        const rows: CapacityUsageRow[] = activeBrands.map((brand) => {
            const configuredValue = configuredTargets[brand.id];
            const isCurrentBrand = Boolean(effectiveBrandId && brand.id === effectiveBrandId);
            return {
                id: brand.id,
                name: brand.name,
                value:
                    typeof configuredValue === "number"
                        ? clampCapacityValue(configuredValue)
                        : isCurrentBrand
                            ? clampCapacityValue(100 - configuredTotalExcludingCurrent)
                            : 0,
                isCurrentBrand,
            };
        });

        if (shouldIncludeNewBrand) {
            rows.push({
                id: NEW_BRAND_CAPACITY_ROW_ID,
                name: formRef.current.core.name.trim() || "New Brand Space",
                value: clampCapacityValue(
                    100 - rows.reduce((sum, row) => sum + row.value, 0),
                ),
                isCurrentBrand: true,
                isNewBrand: true,
            });
        }

        return rows;
    };

    const persistCapacityTargets = async (brand: BrandResponse, rows: CapacityUsageRow[]) => {
        if (!tenantId || !tenant || !rows.length) {
            return;
        }

        await updateBrandUsageTargets.mutateAsync({
            id: tenantId,
            brandUsageTargets: Object.fromEntries(
                rows.map((row) => [row.isNewBrand ? brand.id : row.id, row.value]),
            ),
        });
        await queryClient.invalidateQueries({ queryKey: ["brand", brand.id, "usage"] });
    };

    const applyUploadUpdate = (itemId: string, patch: Parameters<typeof updateBrandUploadItemState>[2]) => {
        setForm((current) => {
            const updated = updateBrandUploadItemState(current, itemId, patch);
            const next = applyExtractedVisualIdentityData(updated, patch, itemId);
            formRef.current = next;
            return next;
        });
    };

    const handleSelectColorPaletteUpload = async (itemId: string) => {
        const targetItem = findBrandUploadItem(formRef.current, itemId);
        if (!targetItem) {
            return;
        }

        if (!targetItem.uploadedAssetId || !effectiveBrandId) {
            setForm((current) => {
                const next = selectColorPaletteUpload(current, itemId);
                formRef.current = next;
                return next;
            });
            return;
        }

        setForm((current) => {
            const next = selectColorPaletteUpload(current, itemId);
            formRef.current = next;
            return next;
        });

        try {
            const asset = await request(API.BRANDS.ATTACHMENT_DETAIL, {
                pathParams: { brandId: effectiveBrandId, assetId: targetItem.uploadedAssetId },
            });
            const patch = attachmentToUploadPatch(asset);
            setForm((current) => {
                if (current.visualIdentity.activeColorPaletteUploadId !== itemId) {
                    return current;
                }
                const updated = updateBrandUploadItemState(current, itemId, patch);
                const next = selectColorPaletteUpload(updated, itemId);
                formRef.current = next;
                return next;
            });
        } catch {
            setForm((current) => {
                const next = selectColorPaletteUpload(current, itemId);
                formRef.current = next;
                return next;
            });
        }
    };

    useEffect(() => {
        if (!effectiveBrandId || !hasPendingUploadItems) {
            return;
        }

        let isCancelled = false;

        const syncDraftStatus = async () => {
            try {
                const [latestBrand, latestValidation] = await Promise.all([
                    request(API.BRANDS.DETAIL, { pathParams: effectiveBrandId }),
                    request(API.BRANDS.VALIDATION, { pathParams: effectiveBrandId }),
                ]);
                if (isCancelled) {
                    return;
                }
                setDraftBrand(latestBrand);
                setBrandLifecycleState(latestBrand.lifecycle_state);
                setValidationSummary(latestValidation);
            } catch {
                return;
            }

            try {
                await syncBrandSpaceAssetStatuses(effectiveBrandId, formRef.current, (update) => {
                    if (isCancelled) {
                        return;
                    }
                    applyUploadUpdate(update.itemId, {
                        uploadedAssetId: update.uploadedAssetId,
                        storagePath: update.storagePath,
                        assetUrl: update.assetUrl || undefined,
                        lifecycleState: update.lifecycleState,
                        channel: update.channel,
                        mimeType: update.mimeType,
                        pageCount: update.pageCount,
                        processingError: update.processingError,
                        templateKind: update.templateKind,
                        analysisJson: update.analysisJson,
                        fieldKey: update.fieldKey,
                        assetCategory: update.assetCategory,
                        validationState: update.validationState,
                        validationSummaryJson: update.validationSummaryJson,
                        structuredDataJson: update.structuredDataJson,
                        normalizedDataJson: update.normalizedDataJson,
                        processingStatus: update.processingStatus,
                        routing: update.routing,
                        isActive: update.isActive,
                    });
                });
            } catch {
                // Leave current UI state intact and try again next poll.
            }
        };

        void syncDraftStatus();
        const timer = window.setInterval(() => {
            void syncDraftStatus();
        }, STATUS_POLL_INTERVAL_MS);

        return () => {
            isCancelled = true;
            window.clearInterval(timer);
        };
    }, [effectiveBrandId, hasPendingUploadItems]);

    const syncQueries = async (brand: BrandResponse) => {
        queryClient.setQueryData(["brand", brand.id], brand);
        queryClient.setQueryData(["brands"], (current: Array<{ id: string }> | undefined) => {
            const items = current || [];
            const next = items.filter((item) => item.id !== brand.id);
            return [brand, ...next];
        });
        await queryClient.invalidateQueries({ queryKey: ["brand", brand.id] });
        await queryClient.invalidateQueries({ queryKey: ["brand", brand.id, "overview"] });
        await queryClient.invalidateQueries({ queryKey: ["brands"] });
    };

    const ensureBrand = async () => {
        if (mode === "edit" && brandId) {
            return request(API.BRANDS.DETAIL, { pathParams: brandId });
        }
        if (draftBrandId) {
            return request(API.BRANDS.DETAIL, { pathParams: draftBrandId });
        }
        return createBrand.mutateAsync(mapBrandFormToCreateRequest(formRef.current));
    };

    const persistSections = async (
        brand: BrandResponse,
        uploadedAssets: UploadedBrandAssets,
        sourceForm: BrandFormState = formRef.current,
    ) => {
        const sectionPayloads = mapBrandSections(sourceForm, uploadedAssets);
        await request(API.BRANDS.UPSERT_SECTIONS, {
            pathParams: brand.id,
            data: {
                sections: sectionPayloads.map((section) => ({
                    section_code: section.section_code,
                    payload: section.payload,
                    completion_percent: section.completion_percent,
                })),
            },
        });
    };

    const handleSubmit = async (intent: "draft" | "publish" | "save", usageRows?: CapacityUsageRow[]) => {
        if (isReadOnly) {
            return;
        }
        if (canOpenWorkspace && intent === "publish") {
            router.push(buildBrandWorkspaceHref(draftBrand as BrandResponse));
            return;
        }

        if (intent === "publish" && !validateRequiredFieldsForPublish()) {
            return;
        }

        setActiveSubmitIntent(intent);
        setSubmissionPhase(
            intent === "draft"
                ? "Saving draft..."
                : intent === "publish"
                    ? "Preparing Brand Space for publishing..."
                    : "Saving Brand Space changes...",
        );
        setIsSubmitting(true);

        try {
            let formSnapshot = formRef.current;
            const isFirstSaveForBrand = mode !== "edit" && !draftBrandId;
            const currentBrand = await ensureBrand();
            setDraftBrand(currentBrand);
            setDraftBrandId(currentBrand.id);
            setBrandLifecycleState(currentBrand.lifecycle_state);
            setHydratedBrandStateId(currentBrand.id);

            if (usageRows?.length) {
                setSubmissionPhase("Saving capacity usage...");
                await persistCapacityTargets(currentBrand, usageRows);
            }

            if (isFirstSaveForBrand) {
                setSubmissionPhase("Saving structured brand data...");
                await persistSections(currentBrand, emptyUploadedBrandAssets, formSnapshot);
            }

            if (hydratedAttachmentBrandId !== currentBrand.id) {
                const existingAttachments = await listBrandSpaceAttachments(currentBrand.id);
                formSnapshot = syncActiveColorPaletteFields(mergeBrandAttachmentsIntoForm(formSnapshot, existingAttachments));
                formRef.current = formSnapshot;
                setForm(formSnapshot);
            }
            setHydratedAttachmentBrandId(currentBrand.id);

            setSubmissionPhase("Uploading and syncing brand files...");
            const uploadedAssets = await uploadBrandSpaceAssets(currentBrand.id, formSnapshot, (update) =>
                applyUploadUpdate(update.itemId, {
                    uploadedAssetId: update.uploadedAssetId,
                    storagePath: update.storagePath,
                    assetUrl: update.assetUrl || undefined,
                    lifecycleState: update.lifecycleState,
                    channel: update.channel,
                    mimeType: update.mimeType,
                    pageCount: update.pageCount,
                    processingError: update.processingError,
                    templateKind: update.templateKind,
                    analysisJson: update.analysisJson,
                    fieldKey: update.fieldKey,
                    assetCategory: update.assetCategory,
                    validationState: update.validationState,
                    validationSummaryJson: update.validationSummaryJson,
                    structuredDataJson: update.structuredDataJson,
                    normalizedDataJson: update.normalizedDataJson,
                    processingStatus: update.processingStatus,
                    routing: update.routing,
                    isActive: update.isActive,
                }),
            );
            const latestAttachments = await listBrandSpaceAttachments(currentBrand.id);
            formSnapshot = syncActiveColorPaletteFields(mergeBrandAttachmentsIntoForm(formRef.current, latestAttachments));
            formRef.current = formSnapshot;
            setForm(formSnapshot);
            setHydratedAttachmentBrandId(currentBrand.id);

            setSubmissionPhase("Saving structured brand sections...");
            await persistSections(currentBrand, uploadedAssets, formSnapshot);

            let nextBrand = currentBrand;
            if (intent === "publish") {
                setSubmissionPhase("Publishing Brand Space...");
                nextBrand = await request(API.BRANDS.PUBLISH, {
                    pathParams: currentBrand.id,
                });
                showSuccessToast(
                    "Brand Space is active",
                    hasPendingBackgroundProcessing(uploadedAssets)
                        ? "File processing will continue in the background, and you can open the workspace right away."
                        : "Brand Space is ready.",
                );
            } else {
                nextBrand = await request(API.BRANDS.DETAIL, {
                    pathParams: currentBrand.id,
                });
                showSuccessToast(
                    intent === "draft" ? "Draft saved" : "Brand Space changes saved",
                    intent === "draft"
                        ? "You can keep editing, add more documents, or publish when you are ready."
                        : undefined,
                );
            }

            const latestValidation = await request(API.BRANDS.VALIDATION, {
                pathParams: currentBrand.id,
            });

            setDraftBrand(nextBrand);
            setDraftBrandId(nextBrand.id);
            setBrandLifecycleState(nextBrand.lifecycle_state);
            setValidationSummary(latestValidation);
            setHydratedBrandStateId(nextBrand.id);
            setHydratedAttachmentBrandId(nextBrand.id);
            await syncQueries(nextBrand);

            if (nextBrand.lifecycle_state === "active" && !hasPendingUploadItems) {
                clearBrandSpaceDraft();
            }
        } catch (error) {
            const detail = axios.isAxiosError(error)
                ? error.response?.data?.detail || error.response?.data?.message || error.message
                : error instanceof Error
                    ? error.message
                    : "Unable to save Brand Space.";
            showErrorToast("Unable to save Brand Space", String(detail));
        } finally {
            setSubmissionPhase(null);
            setIsSubmitting(false);
            setActiveSubmitIntent(null);
        }
    };

    const handleRemoveUpload = async (itemId: string) => {
        if (isReadOnly) {
            return;
        }
        const targetItem = findBrandUploadItem(formRef.current, itemId);
        if (!targetItem) {
            return;
        }
        setActionItemId(itemId);

        try {
            if (targetItem.uploadedAssetId && effectiveBrandId) {
                await request(API.BRANDS.ATTACHMENT_DELETE, {
                    pathParams: { brandId: effectiveBrandId, assetId: targetItem.uploadedAssetId },
                });
            }
            setForm((current) => {
                const next = syncActiveColorPaletteFields(removeBrandUploadItem(current, itemId));
                formRef.current = next;
                return next;
            });
            showSuccessToast("File removed", `Removed ${targetItem.name}.`);
        } catch (error) {
            const detail = axios.isAxiosError(error)
                ? error.response?.data?.detail || error.message
                : error instanceof Error
                    ? error.message
                    : "Unable to remove file.";
            showErrorToast("Unable to remove file", String(detail));
        } finally {
            setActionItemId(null);
        }
    };

    const handleReprocessUpload = async (itemId: string) => {
        if (isReadOnly) {
            return;
        }
        const targetItem = findBrandUploadItem(formRef.current, itemId);
        if (!targetItem?.uploadedAssetId || !effectiveBrandId) {
            return;
        }
        setActionItemId(itemId);
        try {
            const response = await request(API.BRANDS.ATTACHMENT_REPROCESS, {
                pathParams: { brandId: effectiveBrandId, assetId: targetItem.uploadedAssetId },
            });
            applyUploadUpdate(itemId, {
                uploadedAssetId: response.asset.id,
                assetUrl: response.asset.asset_url || undefined,
                storagePath: response.asset.storage_path,
                lifecycleState: response.asset.processing_status?.lifecycle_state || response.asset.lifecycle_state,
                channel: response.asset.channel,
                mimeType: response.asset.mime_type,
                pageCount: response.asset.page_count,
                processingError: response.asset.processing_error,
                fieldKey: response.asset.field_key || undefined,
                assetCategory: response.asset.asset_category || undefined,
                validationState: response.asset.validation_state,
                validationSummaryJson: response.asset.validation_summary_json,
                structuredDataJson: response.asset.structured_data_json,
                normalizedDataJson: response.asset.normalized_data_json,
                processingStatus: response.asset.processing_status || undefined,
                routing: response.asset.routing || undefined,
                isActive: response.asset.is_active,
            });
            showInfoToast("File reprocessing started", response.message);
        } catch (error) {
            const detail = axios.isAxiosError(error)
                ? error.response?.data?.detail || error.message
                : error instanceof Error
                    ? error.message
                    : "Unable to reprocess file.";
            showErrorToast("Unable to reprocess file", String(detail));
        } finally {
            setActionItemId(null);
        }
    };

    const handleUnsyncUpload = async (itemId: string) => {
        if (isReadOnly) {
            return;
        }
        const targetItem = findBrandUploadItem(formRef.current, itemId);
        if (!targetItem?.uploadedAssetId || !effectiveBrandId) {
            return;
        }
        setActionItemId(itemId);
        try {
            const response = await request(API.BRANDS.ATTACHMENT_UNSYNC, {
                pathParams: { brandId: effectiveBrandId, assetId: targetItem.uploadedAssetId },
            });
            applyUploadUpdate(itemId, {
                uploadedAssetId: response.asset.id,
                assetUrl: response.asset.asset_url || undefined,
                storagePath: response.asset.storage_path,
                lifecycleState: response.asset.processing_status?.lifecycle_state || response.asset.lifecycle_state,
                channel: response.asset.channel,
                mimeType: response.asset.mime_type,
                pageCount: response.asset.page_count,
                processingError: response.asset.processing_error,
                fieldKey: response.asset.field_key || undefined,
                assetCategory: response.asset.asset_category || undefined,
                validationState: response.asset.validation_state,
                validationSummaryJson: response.asset.validation_summary_json,
                structuredDataJson: response.asset.structured_data_json,
                normalizedDataJson: response.asset.normalized_data_json,
                processingStatus: response.asset.processing_status || undefined,
                routing: response.asset.routing || undefined,
                isActive: response.asset.is_active,
            });
            showWarningToast("File unsynced", response.message);
        } catch (error) {
            const detail = axios.isAxiosError(error)
                ? error.response?.data?.detail || error.message
                : error instanceof Error
                    ? error.message
                    : "Unable to unsync file.";
            showErrorToast("Unable to unsync file", String(detail));
        } finally {
            setActionItemId(null);
        }
    };

    const handleUnpublish = async () => {
        if (isReadOnly) {
            return;
        }
        if (!effectiveBrandId) {
            return;
        }
        setSubmissionPhase("Moving Brand Space back to draft...");
        setActiveSubmitIntent("unpublish");
        setIsSubmitting(true);
        try {
            const brand = await request(API.BRANDS.UNPUBLISH, {
                pathParams: effectiveBrandId,
            });
            const latestValidation = await request(API.BRANDS.VALIDATION, {
                pathParams: effectiveBrandId,
            });
            setDraftBrand(brand);
            setBrandLifecycleState(brand.lifecycle_state);
            setValidationSummary(latestValidation);
            await syncQueries(brand);
            showWarningToast(
                "Brand Space moved back to draft",
                "You can keep editing and publish again later.",
            );
        } catch (error) {
            const detail = axios.isAxiosError(error)
                ? error.response?.data?.detail || error.message
                : error instanceof Error
                    ? error.message
                    : "Unable to move Brand Space to draft.";
            showErrorToast("Unable to move Brand Space to draft", String(detail));
        } finally {
            setSubmissionPhase(null);
            setIsSubmitting(false);
            setActiveSubmitIntent(null);
        }
    };

    const handleOpenBrandSpace = () => {
        if (!effectiveBrandId) {
            return;
        }
        if (!hasPendingUploadItems) {
            clearBrandSpaceDraft();
        }
        router.push(
            buildBrandWorkspaceHref({
                id: effectiveBrandId,
                slug: draftBrand?.slug ?? effectiveBrandId,
            }),
        );
    };

    const handlePrimarySubmit = () => {
        if (isReadOnly) {
            return;
        }
        if (primarySubmitIntent === "publish") {
            if (!validateRequiredFieldsForPublish()) {
                return;
            }
            setCapacityRows(buildCapacityRows());
            setCapacityError(null);
            setCapacityDialogOpen(true);
            return;
        }

        if (requiresPublishedEditConfirmation) {
            setEditConfirmationOpen(true);
            return;
        }

        void handleSubmit(primarySubmitIntent);
    };

    const handleCapacityRowChange = (rowId: string, value: string) => {
        if (isReadOnly) {
            return;
        }
        const nextValue = parseCapacityValue(value);
        setCapacityRows((current) =>
            current.map((row) => (row.id === rowId ? { ...row, value: nextValue } : row)),
        );
        setCapacityError(null);
    };

    const handleConfirmCapacityUsage = () => {
        if (isReadOnly) {
            return;
        }
        if (!tenantId || !tenant) {
            setCapacityError("Tenant context is missing. Please refresh and try again.");
            return;
        }
        if (!capacityRows.length) {
            setCapacityError("Add capacity usage before publishing this Brand Space.");
            return;
        }
        if (capacityTotal > 100) {
            setCapacityError("Total capacity usage cannot be more than 100%.");
            return;
        }
        setCapacityDialogOpen(false);
        void handleSubmit("publish", capacityRows);
    };

    return (
        <div className="container space-y-6">
            <PageHeading
                title={
                    mode === "create"
                        ? canOpenWorkspace
                            ? "Brand Space Ready"
                            : "Create Brand Space"
                        : isReadOnly
                            ? "View Brand Space"
                            : "Edit Brand Space"
                }
                actions={
                    <div className="flex flex-wrap items-center justify-end gap-3">
                        {canOpenWorkspace ? (
                            <Button
                                onClick={handleOpenBrandSpace}
                                className="flex items-center justify-center gap-2 rounded-none bg-primary/72 p-6 text-base hover:bg-primary/90"
                            >
                                <Eye className="h-4 w-4" />
                                <span>Open Studio</span>
                            </Button>
                        ) : null}

                        {!isReadOnly && brandLifecycleState !== "active" ? (
                            <Button
                                type="button"
                                variant="outline"
                                disabled={createBrand.isPending || isSubmitting}
                                className="rounded-none border-slate-300 p-6 text-base"
                                onClick={() => void handleSubmit("draft")}
                            >
                                {isDraftSubmitting
                                    ? draftBrandId
                                        ? "Saving..."
                                        : "Creating..."
                                    : draftBrandId
                                        ? "Save Draft"
                                        : "Create Draft"}
                            </Button>
                        ) : null}

                        {!isReadOnly && brandLifecycleState === "active" ? (
                            <Button
                                type="button"
                                variant="outline"
                                disabled={isSubmitting}
                                className="rounded-none border-amber-300 p-6 text-base text-amber-700 hover:bg-amber-50"
                                onClick={() => void handleUnpublish()}
                            >
                                {isUnpublishSubmitting ? "Moving..." : "Move to Draft"}
                            </Button>
                        ) : null}

                        {!isReadOnly ? (
                            <Button
                                type="button"
                                variant="outline"
                                disabled={
                                    createBrand.isPending ||
                                    isSubmitting ||
                                    autofillFromKnowledge.isPending ||
                                    !(draftBrandId || brandId)
                                }
                                className="flex items-center justify-center gap-2 rounded-none border-primary/30 p-6 text-base text-primary hover:bg-primary/5"
                                onClick={() => void handleAutofillFromKnowledge()}
                            >
                                {autofillFromKnowledge.isPending ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Sparkles className="h-4 w-4" />
                                )}
                                <span>
                                    {autofillFromKnowledge.isPending
                                        ? "Fetching from knowledge..."
                                        : "Auto-fill from knowledge"}
                                </span>
                            </Button>
                        ) : null}

                        {!isReadOnly ? (
                            <Button
                                onClick={handlePrimarySubmit}
                                disabled={createBrand.isPending || isSubmitting}
                                className="flex items-center justify-center gap-2 rounded-none bg-primary/72 p-6 text-base hover:bg-primary/90"
                            >
                                <span>
                                    {isPrimarySubmitting
                                        ? primarySubmitIntent === "save"
                                            ? "Saving..."
                                            : "Publishing..."
                                        : primarySubmitIntent === "save"
                                            ? "Save Changes"
                                            : "Publish Brand Space"}
                                </span>
                            </Button>
                        ) : null}

                        {canShowHistoryButton ? (
                            <BrandSpaceHistoryDrawer brandId={effectiveBrandId}>
                                <Button
                                    type="button"
                                    variant="outline"
                                    aria-label="History"
                                    title="History"
                                    className="max-w-12 flex items-center justify-center rounded-none bg-primary/5 p-6 text-base hover:bg-primary/15"
                                >
                                    <Clock3 className="h-5 w-5" />
                                </Button>
                            </BrandSpaceHistoryDrawer>
                        ) : null}
                    </div>
                }
            />

            {/* <ValidationSummaryPanel lifecycleState={brandLifecycleState} summary={validationSummary} /> */}


            {canOpenWorkspace && hasPendingUploadItems ? (
                <div className="rounded-xl border border-primary/15 bg-primary/5 px-4 py-3 text-sm text-primary">
                    This Brand Space is already active. File processing is still running in the background, so you can leave this page and come back later to check status.
                </div>
            ) : null}

            <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
                <div className="space-y-5 pt-7">
                    <div className="overflow-x-auto w-full border-b border-slate-200 pb-2 scrollbar-thin">
                    <TabsList className="flex h-auto flex-nowrap justify-start gap-1 bg-transparent p-0 overflow-visible w-max min-w-full">
                        {brandSpaceTabs.map((tab) => {
                            const completion = tabCompletion[tab.value] ?? { percent: 100, required: 0, completed: 0 };
                            const fillPercent = Math.max(0, Math.min(100, completion.percent));
                            const showCompletionLabel = !["brand_knowledge", "additional_details"].includes(tab.value);
                            return (
                                <TabsTrigger
                                    key={tab.id}
                                    value={tab.value}
                                    className={cn(
                                        "group relative overflow-visible rounded-lg border border-[#CDCDCD] bg-white p-1.5 text-[15px] shadow-none hover:bg-[#F7F7FB] data-[state=active]:font-bold",
                                        fillPercent === 100 ? "border-primary/40" : "",
                                    )}
                                >
                                    {showCompletionLabel ? (
                                        <span className="pointer-events-none absolute -top-6 left-1/2 z-20 inline-flex -translate-x-1/2 whitespace-nowrap rounded-sm bg-primary px-1.5 py-0.5 text-[10px] font-medium text-white">
                                            {fillPercent}% Completed
                                        </span>
                                    ) : null}
                                    <span
                                        className="rounded-md px-3 py-2"
                                        style={{
                                            backgroundImage: `linear-gradient(90deg, rgba(201, 201, 201, 1) ${fillPercent}%, transparent ${fillPercent}%)`,
                                        }}
                                    >
                                        {tab.label}
                                    </span>
                                </TabsTrigger>
                            );
                        })}
                    </TabsList>
                    </div>
                </div>

                <div className="pt-2">
                    {brandSpaceTabs.map((tab) => {
                        if (tab.value !== activeTab) {
                            return null;
                        }
                        const TabComponent = tab.content;
                        return (
                            <TabsContent key={tab.id} value={tab.value} className="w-full">
                                <fieldset
                                    disabled={isReadOnly}
                                    className={cn(isReadOnly ? "pointer-events-none opacity-95" : "")}
                                >
                                    <TabComponent
                                        brandId={effectiveBrandId || ""}
                                        form={form}
                                        setForm={isReadOnly ? readOnlySetForm : setForm}
                                        onRemoveUpload={isReadOnly ? undefined : handleRemoveUpload}
                                        onSelectColorPaletteUpload={isReadOnly ? undefined : handleSelectColorPaletteUpload}
                                    />
                                </fieldset>
                            </TabsContent>
                        );
                    })}
                </div>
            </Tabs>

            {!isReadOnly ? (
                <UploadStatusPanel
                    items={uploadStatusItems}
                    isSubmitting={isSubmitting}
                    actionItemId={actionItemId}
                    onReprocess={handleReprocessUpload}
                    onUnsync={handleUnsyncUpload}
                    onRemove={handleRemoveUpload}
                />
            ) : null}


            {submissionPhase ? (
                <div className="rounded-xl border border-primary/15 bg-primary/5 px-4 py-3 text-sm text-primary">
                    {submissionPhase}
                </div>
            ) : null}

            <Dialog open={capacityDialogOpen} onOpenChange={setCapacityDialogOpen}>
                <DialogContent className="max-w-[727px] min-w-[650px] rounded-none border-0 bg-white p-5 shadow-[0_24px_80px_-28px_rgba(15,23,42,0.45)]">
                    <DialogHeader className="gap-1">
                        <DialogTitle className="text-[24px] font-bold leading-tight text-primary">
                            Set Capacity Usage
                        </DialogTitle>
                        <DialogDescription className="text-sm text-[#121212]">
                            This does not restrict usage. It helps track usage and triggers alerts as the limit approaches.
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-6">
                        <div className="max-w-[252px] flex flex-col gap-2">
                            <label className="text-base font-medium text-[#121212]" htmlFor="new-brand-capacity">
                                Capacity Usage
                            </label>
                            <input
                                id="new-brand-capacity"
                                inputMode="numeric"
                                placeholder="Enter percentage"
                                value={currentBrandCapacityRow?.value ?? ""}
                                onChange={(event) =>
                                    currentBrandCapacityRow && handleCapacityRowChange(currentBrandCapacityRow.id, event.target.value)
                                }
                                className="h-12 w-full rounded-[10px] border-none bg-[#F5F7FA] px-3 text-sm text-[#121212] outline-none transition placeholder:text-[#A1A1AA] focus:ring-2 focus:ring-primary/20"
                            />
                        </div>

                        <div className="space-y-2">
                            <h3 className="text-xl font-semibold text-[#121212]">Usage Overview</h3>
                            <div className="grid grid-cols-2 gap-1 text-sm font-medium text-[#121212]">
                                <div className="bg-[#F5F6FA] px-3 py-3">Brand</div>
                                <div className="bg-[#F5F6FA] px-3 py-3">Usage</div>
                            </div>
                            <div className="space-y-1">
                                {capacityRows.map((row) => (
                                    <div key={row.id} className="grid grid-cols-2 gap-1">
                                        <h2 className="bg-[#F5F6FA] px-3 py-3 text-sm text-[#121212]">{row.name}</h2>
                                        <input
                                            aria-label={`${row.name} capacity usage`}
                                            inputMode="numeric"
                                            value={row.value}
                                            onChange={(event) => handleCapacityRowChange(row.id, event.target.value)}
                                            className="min-w-0 bg-[#F5F6FA] px-3 py-2 text-sm text-[#121212] outline-none transition focus:ring-2 focus:ring-primary/20"
                                        />
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <p className="text-sm text-[#6B7280]">
                                Current total allocation: {capacityTotal}%
                            </p>
                            {capacityError ? <p className="text-sm text-red-500">{capacityError}</p> : null}
                        </div>

                        <div className="flex justify-end gap-3 pt-1">
                            <Button
                                type="button"
                                variant="outline"
                                onClick={() => setCapacityDialogOpen(false)}
                                className="rounded-none border-slate-300 p-5"
                            >
                                Cancel
                            </Button>
                            <Button
                                type="button"
                                onClick={handleConfirmCapacityUsage}
                                disabled={isSubmitting || updateBrandUsageTargets.isPending}
                                className="rounded-none bg-primary/72 p-5 hover:bg-primary/90"
                            >
                                {isSubmitting || updateBrandUsageTargets.isPending ? "Creating..." : "Create Brand Space"}
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            <AlertDialog open={editConfirmationOpen} onOpenChange={setEditConfirmationOpen}>
                <AlertDialogContent className="max-w-[420px] rounded-none border-0 bg-white p-6 shadow-[0_20px_80px_-24px_rgba(15,23,42,0.35)]">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Edit Brand Space?</AlertDialogTitle>
                        <AlertDialogDescription>
                            Updating the Brand Space will affect future creative outputs. Are you sure you want to proceed with these changes?
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel className="w-22 h-12 rounded-none">No</AlertDialogCancel>
                        <AlertDialogAction
                            onClick={(event) => {
                                event.preventDefault();
                                setEditConfirmationOpen(false);
                                void handleSubmit("save");
                            }}
                            className="w-22 h-12 rounded-none bg-primary/72 text-white hover:bg-primary/90"
                            disabled={isSubmitting}
                        >
                            Yes
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>

            {/*<p className="absolute bottom-2 left-1/4 mx-auto pt-8 text-center text-sm text-[#929292]">
                Violyt suggestions may need review. Verify accuracy before use.
            </p> */}
        </div>
    );
}
