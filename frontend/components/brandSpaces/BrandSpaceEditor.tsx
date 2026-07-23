"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
    AlertCircle,
    CheckCircle2,
    Eye,
    FileText,
    Loader2,
    RefreshCw,
    Sparkles,
    Unplug,
} from "lucide-react";
import { Button } from "@/components/ui/button";
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
import type { BrandResponse, ValidationSummaryResponse } from "@/lib/api/contracts";
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
import { useUpdateTenantAdmin } from "@/hooks/tenantAdmins/useUpdateTenant";
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
    mode: "create" | "edit";
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

function isSyncedUploadPatch(patch: UploadStatePatch) {
    const state = normalizeUploadState(
        patch.lifecycleState || patch.processingStatus?.lifecycle_state,
    );
    return ["indexed", "complete", "ready"].includes(state);
}

function applyExtractedVisualIdentityData(form: BrandFormState, patch: UploadStatePatch): BrandFormState {
    if (!isSyncedUploadPatch(patch)) {
        return form;
    }

    const fieldKey = String(patch.fieldKey || "").trim();
    const assetCategory = String(patch.assetCategory || "").trim();
    const structuredData = patch.structuredDataJson || {};
    let visualIdentity = form.visualIdentity;
    let changed = false;

    if (fieldKey === "color_palette" || assetCategory === "color_palette") {
        const entries = Array.isArray(structuredData.palette_entries)
            ? structuredData.palette_entries.map(toRecord).filter((entry) => extractedHex(entry))
            : [];
        if (entries.length) {
            const primary = entries.find((entry) => extractedRole(entry) === "primary") || entries[0];
            const secondary = entries.find((entry) => extractedRole(entry) === "secondary") || entries[1];
            const additional = entries.filter((entry) => ![primary, secondary].includes(entry));
            const nextVisualIdentity = { ...visualIdentity };

            if (!nextVisualIdentity.primaryColor && primary) {
                nextVisualIdentity.primaryColor = extractedHex(primary);
                changed = true;
            }
            if (!nextVisualIdentity.secondaryColor && secondary) {
                nextVisualIdentity.secondaryColor = extractedHex(secondary);
                changed = true;
            }
            if (
                additional.length &&
                !nextVisualIdentity.additionalColors.some((color) => color.name.trim() || color.hex.trim())
            ) {
                nextVisualIdentity.additionalColors = additional.map((entry) => ({
                    name: String(entry.color_name || entry.name || extractedRole(entry) || "Additional color"),
                    hex: extractedHex(entry),
                }));
                changed = true;
            }
            visualIdentity = nextVisualIdentity;
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
        <div className="rounded-2xl border border-[#E3E6F2] bg-white px-5 py-4 shadow-[0_14px_32px_-28px_rgba(15,23,42,0.65)]">
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
                    </div>
                </div>
                <CollapsibleContent className="flex flex-col gap-2">

            <div className="mt-4 max-h-100 space-y-2 overflow-auto pr-1">
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
    const updateTenant = useUpdateTenantAdmin();
    const { data: currentUser } = useGetMe();
    const tenantId = currentUser?.tenantId ?? "";
    const { data: tenant } = useGetTenantData(tenantId);
    const { data: brands } = useBrands();

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
    const [hasActivatedAttachmentTab, setHasActivatedAttachmentTab] = useState(false);
    const [hydratedBrandStateId, setHydratedBrandStateId] = useState<string | null>(null);
    const [hydratedAttachmentBrandId, setHydratedAttachmentBrandId] = useState<string | null>(null);
    const [capacityDialogOpen, setCapacityDialogOpen] = useState(false);
    const [capacityRows, setCapacityRows] = useState<CapacityUsageRow[]>([]);
    const [capacityError, setCapacityError] = useState<string | null>(null);
    const formRef = useRef(form);

    useEffect(() => {
        formRef.current = form;
    }, [form]);

    useEffect(() => {
        if (mode !== "edit") {
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
        setHasActivatedAttachmentTab(false);
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
            setHasActivatedAttachmentTab(false);
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
        if (mode !== "create" || !didHydrateDraft) {
            return;
        }
        saveBrandSpaceDraft({
            brandId: draftBrandId,
            lifecycleState: brandLifecycleState,
            form,
        });
    }, [brandLifecycleState, didHydrateDraft, draftBrandId, form, mode]);

    const effectiveBrandId = draftBrandId ?? brandId ?? null;
    const activeTabNeedsAttachments = hasActivatedAttachmentTab && ATTACHMENT_TAB_VALUES.has(activeTab);

    const handleTabChange = (nextTab: string) => {
        setActiveTab(nextTab);
        if (ATTACHMENT_TAB_VALUES.has(nextTab)) {
            setHasActivatedAttachmentTab(true);
        }
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
                    const merged = mergeBrandAttachmentsIntoForm(current, attachments);
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
    const canOpenWorkspace = Boolean(draftBrand?.id) && brandLifecycleState === "active";
    const primarySubmitIntent: "publish" | "save" =
        brandLifecycleState === "active" || hasUnsavedUploadItems ? "save" : "publish";
    const isDraftSubmitting = isSubmitting && activeSubmitIntent === "draft";
    const isUnpublishSubmitting = isSubmitting && activeSubmitIntent === "unpublish";
    const isPrimarySubmitting =
        isSubmitting && (activeSubmitIntent === "publish" || activeSubmitIntent === "save");
    const capacityTotal = capacityRows.reduce((sum, row) => sum + row.value, 0);
    const currentBrandCapacityRow = capacityRows.find((row) => row.isCurrentBrand || row.isNewBrand);

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

        await updateTenant.mutateAsync({
            id: tenantId,
            data: {
                metadata_json: {
                    ...(tenant.metadata_json || {}),
                    brand_usage_targets: Object.fromEntries(
                        rows.map((row) => [row.isNewBrand ? brand.id : row.id, row.value]),
                    ),
                },
            },
        });
        await queryClient.invalidateQueries({ queryKey: ["brand", brand.id, "usage"] });
    };

    const applyUploadUpdate = (itemId: string, patch: Parameters<typeof updateBrandUploadItemState>[2]) => {
        setForm((current) => {
            const updated = updateBrandUploadItemState(current, itemId, patch);
            const next = applyExtractedVisualIdentityData(updated, patch);
            formRef.current = next;
            return next;
        });
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
                formSnapshot = mergeBrandAttachmentsIntoForm(formSnapshot, existingAttachments);
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
            formSnapshot = mergeBrandAttachmentsIntoForm(formRef.current, latestAttachments);
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
            setForm((current) => removeBrandUploadItem(current, itemId));
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
        if (!draftBrand) {
            return;
        }
        if (!hasPendingUploadItems) {
            clearBrandSpaceDraft();
        }
        router.push(buildBrandWorkspaceHref(draftBrand));
    };

    const handlePrimarySubmit = () => {
        if (primarySubmitIntent === "publish") {
            if (!validateRequiredFieldsForPublish()) {
                return;
            }
            setCapacityRows(buildCapacityRows());
            setCapacityError(null);
            setCapacityDialogOpen(true);
            return;
        }

        void handleSubmit(primarySubmitIntent);
    };

    const handleCapacityRowChange = (rowId: string, value: string) => {
        const nextValue = parseCapacityValue(value);
        setCapacityRows((current) =>
            current.map((row) => (row.id === rowId ? { ...row, value: nextValue } : row)),
        );
        setCapacityError(null);
    };

    const handleConfirmCapacityUsage = () => {
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
                                <span>Open Brand Space</span>
                            </Button>
                        ) : null}

                        {brandLifecycleState !== "active" ? (
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

                        {brandLifecycleState === "active" ? (
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
                    </div>
                }
            />

            {/* <ValidationSummaryPanel lifecycleState={brandLifecycleState} summary={validationSummary} /> */}

            <UploadStatusPanel
                items={uploadStatusItems}
                isSubmitting={isSubmitting}
                actionItemId={actionItemId}
                onReprocess={handleReprocessUpload}
                onUnsync={handleUnsyncUpload}
                onRemove={handleRemoveUpload}
            />

            {canOpenWorkspace && hasPendingUploadItems ? (
                <div className="rounded-xl border border-primary/15 bg-primary/5 px-4 py-3 text-sm text-primary">
                    This Brand Space is already active. File processing is still running in the background, so you can leave this page and come back later to check status.
                </div>
            ) : null}

            <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
                <div className="space-y-5">
                    <TabsList className="flex h-auto flex-nowrap justify-start gap-1 bg-transparent p-0 overflow-x-auto w-full border-b border-slate-200 pb-2 scrollbar-thin">
                        {brandSpaceTabs.map((tab) => {
                            const completion = tabCompletion[tab.value] ?? { percent: 100, required: 0, completed: 0 };
                            const fillPercent = Math.max(0, Math.min(100, completion.percent));
                            return (
                                <TabsTrigger
                                    key={tab.id}
                                    value={tab.value}
                                    className={cn(
                                        "group relative overflow-visible rounded-lg border border-[#CDCDCD] bg-white px-2.5 py-1.5 text-xs shadow-none hover:bg-[#CDCDCD]/20 data-[state=active]:font-bold data-[state=active]:border-black data-[state=active]:border-2 shrink-0",
                                        fillPercent === 100 ? "border-primary/40" : "",
                                    )}
                                    style={{
                                        backgroundImage: `linear-gradient(90deg, rgba(201, 201, 201, 1) ${fillPercent}%, transparent ${fillPercent}%)`,
                                    }}
                                >
                                    <span className="pointer-events-none absolute -top-6 left-1/2 z-20 hidden -translate-x-1/2 whitespace-nowrap rounded-sm bg-primary px-1.5 py-0.5 text-[10px] font-medium text-white group-hover:inline-flex">
                                        {fillPercent}% Completed
                                    </span>
                                    {tab.label}
                                </TabsTrigger>
                            );
                        })}
                    </TabsList>
                </div>

                <div className="pt-2">
                    {brandSpaceTabs.map((tab) => {
                        if (tab.value !== activeTab) {
                            return null;
                        }
                        const TabComponent = tab.content;
                        return (
                            <TabsContent key={tab.id} value={tab.value} className="w-full">
                                <TabComponent brandId={effectiveBrandId || ""} form={form} setForm={setForm} onRemoveUpload={handleRemoveUpload} />
                            </TabsContent>
                        );
                    })}
                </div>
            </Tabs>

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
                                disabled={isSubmitting || updateTenant.isPending}
                                className="rounded-none bg-primary/72 p-5 hover:bg-primary/90"
                            >
                                {isSubmitting || updateTenant.isPending ? "Creating..." : "Create Brand Space"}
                            </Button>
                        </div>
                    </div>
                </DialogContent>
            </Dialog>

            <p className="absolute bottom-2 left-1/4 mx-auto pt-8 text-center text-sm text-[#929292]">
                Violyt suggestions may need review. Verify accuracy before use.
            </p>
        </div>
    );
}
