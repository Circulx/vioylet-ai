"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import {
    ArrowUp,
    BadgePlus,
    Download,
    Loader2,
    Megaphone,
    Paperclip,
    PanelRightClose,
    PanelRightOpen,
    Plus,
    RefreshCw,
    Search,
    Share2,
    Sparkles,
    Square,
    Wand2,
    X,
    ChevronDown,
    ChevronUp,
    PanelLeftOpen,
    PanelLeftClose,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { SurfaceCard, UsageRing } from "@/components/common/DesignPrimitives";
import type {
    AssetReference,
    ChatAssistantStructuredPayload,
    ChatMessageResponse,
    ChatSessionResponse,
    CreativeBlueprintResponse,
    GenerationDecision,
    KnowledgeAssetResponse,
    StudioPanelSelection,
    TemplateRecommendationResponse,
} from "@/lib/api/contracts";
import { buildBrandChatHref, buildBrandSharingHref, resolveBrandByRouteKey } from "@/lib/brand-routing";
import { useBrandUsage, useBrands } from "@/hooks/useBrands";
import { usePipeline } from "@/hooks/usePipeline";
import ChatPipelinePanel, {
    type ChatPipelineState,
} from "@/components/chat/ChatPipelinePanel";
import {
    useChatMessages,
    useChatSessions,
    useCancelChatGeneration,
    useCreateChatSession,
    useSendChatMessage,
    useTemplateRecommendations,
    useToneCheck,
    useUploadKnowledgeAsset,
} from "@/hooks/useContentWorkspace";
import { fileToDataUrl, stripFileExtension } from "@/lib/file-utils";
import {
    coerceGenerationDecision,
    formatGenerationMode,
    getGenerationDecisionConfidence,
    getGenerationDecisionReasons,
    getGenerationDecisionTemplate,
    getGenerationDecisionTemplatePreview,
    getRecommendationConfidence,
} from "@/lib/generation-decision";
import { FormField, StyledInput, StyledSelect } from "../brandSpaces/tabs/FormFields";
import Image from "next/image";
import { AUDIENCE_OPTIONS } from "@/lib/brand-space-options";
import { Label } from "../ui/label";

type WorkspaceChatProps = { brandKey: string };
type ActionMode = "none" | "idea" | "social" | "repurpose" | "alignment";
type Platform = "instagram" | "linkedin" | "x" | "youtube_thumbnail";
type FormatMode = "static" | "carousel" | "infographic" | "video";
type FileType = "doc" | "pdf" | "jpg" | "png";

const actionOptions = [
    { id: "idea", label: "Generate Campaign Idea", icon: "/actions_icons/chat/generate_idea.svg" },
    { id: "social", label: "Create Social Media Post", icon: "/actions_icons/chat/social_media.svg" },
    { id: "repurpose", label: "Repurpose Content", icon: "/actions_icons/chat/repurpose_content.svg" },
    { id: "alignment", label: "Check Brand Alignment", icon: "/actions_icons/chat/brand_alignment.svg" },
] as const;
const actionOptionById = Object.fromEntries(actionOptions.map((action) => [action.id, action])) as Record<
    Exclude<ActionMode, "none">,
    (typeof actionOptions)[number]
>;

const platformOptions: Platform[] = ["linkedin", "instagram", "x"];
const chatPlatformOptions: Platform[] = ["linkedin", "instagram", "x"];
const platformLabels: Record<Platform, string> = {
    instagram: "Instagram",
    linkedin: "LinkedIn",
    x: "X",
    youtube_thumbnail: "YouTube",
};
const formatOptions: Array<{ value: FormatMode; label: string; enabled: boolean }> = [
    { value: "static", label: "Static", enabled: true },
    { value: "carousel", label: "Carousel", enabled: true },
    { value: "infographic", label: "Infographic", enabled: true },
    { value: "video", label: "Video", enabled: false },
];
const fileTypeOptions: FileType[] = ["doc", "pdf", "jpg", "png"];
const campaignGoalOptions = [
    "Brand Awareness",
    "Authority Building",
    "Trust & Credibility",
    "Consideration Influence",
    "Engagement Activation",
    "Community Growth",
];
const campaignObjectiveOptions = [
    "Brand Awareness",
    "Lead Generation",
    "User Acquisition",
    "Engagement Growth",
    "Product Launch Promotion",
    "Customer Retention",
    "Community Building",
    "Event Promotion",
    "Thought Leadership",
];

/** Correct export dimensions by format + platform (matches pipeline L8 sizes). */
const sizeOptionsByFormatPlatform: Record<
    Exclude<FormatMode, "video">,
    Partial<Record<Platform, Array<{ label: string; width: number; height: number }>>>
> = {
    static: {
        linkedin: [
            { label: "1.91:1 · 1200×627", width: 1200, height: 627 },
            { label: "1:1 · 1080×1080", width: 1080, height: 1080 },
        ],
        instagram: [
            { label: "1:1 · 1080×1080", width: 1080, height: 1080 },
            { label: "4:5 · 1080×1350", width: 1080, height: 1350 },
            { label: "9:16 · 1080×1920", width: 1080, height: 1920 },
        ],
        x: [
            { label: "16:9 · 1200×675", width: 1200, height: 675 },
            { label: "1:1 · 1080×1080", width: 1080, height: 1080 },
        ],
    },
    carousel: {
        linkedin: [{ label: "1:1 · 1080×1080", width: 1080, height: 1080 }],
        instagram: [{ label: "1:1 · 1080×1080", width: 1080, height: 1080 }],
        x: [{ label: "1:1 · 1080×1080", width: 1080, height: 1080 }],
    },
    infographic: {
        linkedin: [{ label: "4:5 · 1080×1350", width: 1080, height: 1350 }],
        instagram: [{ label: "4:5 · 1080×1350", width: 1080, height: 1350 }],
        x: [{ label: "4:5 · 1080×1350", width: 1080, height: 1350 }],
    },
};

function resolveSizeOptions(format: FormatMode, platform: Platform) {
    const fmt = format === "video" ? "static" : format;
    const byFormat = sizeOptionsByFormatPlatform[fmt];
    return (
        byFormat[platform] ||
        byFormat.linkedin ||
        [{ label: "1:1 · 1080×1080", width: 1080, height: 1080 }]
    );
}

/** Alias for action-form platform resets */
const sizeOptionsByPlatform: Record<Platform, Array<{ label: string; width: number; height: number }>> = {
    instagram: resolveSizeOptions("static", "instagram"),
    linkedin: resolveSizeOptions("static", "linkedin"),
    x: resolveSizeOptions("static", "x"),
    youtube_thumbnail: [{ label: "16:9 · 1280×720", width: 1280, height: 720 }],
};

const MAX_COMPOSER_HEIGHT = 220;
const GENERATION_PROGRESS_MESSAGES = [
    {
        eyebrow: "Now",
        title: "Reading your brief",
        body: "Lining it up with the brand voice, platform, and format you picked.",
    },
    {
        eyebrow: "Did you know?",
        title: "Violyt can reuse brand-safe assets",
        body: "Uploaded logos, references, and validated brand rules all help keep outputs more consistent.",
    },
    {
        eyebrow: "Now",
        title: "Shaping the message",
        body: "Balancing the hook, body copy, CTA, and visual direction for this creative.",
    },
    {
        eyebrow: "Did you know?",
        title: "One brief can drive multiple formats",
        body: "The same intent can be adapted into static posts, carousels, infographics, and more.",
    },
    {
        eyebrow: "Now",
        title: "Building the visual direction",
        body: "Bringing together layout, imagery, brand color balance, and the strongest available logo path.",
    },
    {
        eyebrow: "Did you know?",
        title: "Brand knowledge keeps getting smarter",
        body: "Templates, docs, and uploaded references help future generations stay closer to your brand.",
    },
    {
        eyebrow: "Now",
        title: "Polishing the final creative",
        body: "Checking the finishing details so we can show the cleanest version possible.",
    },
] as const;

function formatGenerationStatusLine(entry: (typeof GENERATION_PROGRESS_MESSAGES)[number]) {
    if (entry.eyebrow.toLowerCase().includes("did you know")) {
        return `${entry.eyebrow} ${entry.body}`;
    }
    return entry.title;
}

function escapeRegExp(value: string) {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function countSearchOccurrences(text: string, searchQuery: string) {
    const trimmedQuery = searchQuery.trim();
    if (!trimmedQuery) {
        return 0;
    }
    return text.match(new RegExp(escapeRegExp(trimmedQuery), "gi"))?.length || 0;
}

function formatChatHistoryDate(value: string) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return "";
    }
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function HighlightedMessageText({
    text,
    searchQuery,
    activeOccurrenceIndex,
}: {
    text: string;
    searchQuery: string;
    activeOccurrenceIndex: number | null;
}) {
    const trimmedQuery = searchQuery.trim();
    if (!trimmedQuery) {
        return <>{text}</>;
    }

    const parts = text.split(new RegExp(`(${escapeRegExp(trimmedQuery)})`, "gi"));
    let occurrenceIndex = -1;
    return (
        <>
            {parts.map((part, index) => {
                if (part.toLowerCase() !== trimmedQuery.toLowerCase()) {
                    return <span key={`${part}-${index}`}>{part}</span>;
                }
                occurrenceIndex += 1;
                const isActiveMatch = occurrenceIndex === activeOccurrenceIndex;
                return (
                        <mark
                            key={`${part}-${index}`}
                            className={isActiveMatch ? "bg-yellow-300 px-0.5 text-inherit" : "bg-yellow-100 px-0.5 text-inherit"}
                        >
                            {part}
                        </mark>
                );
            })}
        </>
    );
}

function useDebouncedValue<T>(value: T, delayMs: number) {
    const [debouncedValue, setDebouncedValue] = useState(value);

    useEffect(() => {
        const timeout = window.setTimeout(() => setDebouncedValue(value), delayMs);
        return () => window.clearTimeout(timeout);
    }, [delayMs, value]);

    return debouncedValue;
}

function resizeComposer(node: HTMLTextAreaElement | null) {
    if (!node) {
        return;
    }
    node.style.height = "0px";
    const nextHeight = Math.min(node.scrollHeight, MAX_COMPOSER_HEIGHT);
    node.style.height = `${Math.max(nextHeight, 44)}px`;
    node.style.overflowY = node.scrollHeight > MAX_COMPOSER_HEIGHT ? "auto" : "hidden";
}

function dedupeImageAssets(assets: AssetReference[]) {
    const seen = new Set<string>();
    return assets.filter((asset) => {
        const key = asset.asset_url || asset.storage_path || asset.asset_id;
        if (!key || seen.has(key)) {
            return false;
        }
        seen.add(key);
        return true;
    });
}

function resolveGeneratedImageAssets(payload: ChatAssistantStructuredPayload | Record<string, unknown> | undefined) {
    if (!payload || Array.isArray(payload)) {
        return [];
    }
    const typedPayload = payload as ChatAssistantStructuredPayload;
    const exportImages = (typedPayload.export_assets || []).filter(
        (asset) => asset.mime_type.startsWith("image/") && Boolean(asset.asset_url),
    );
    if (exportImages.length) {
        return dedupeImageAssets(exportImages);
    }
    if (typedPayload.preview_asset?.asset_url && typedPayload.preview_asset.mime_type.startsWith("image/")) {
        return [typedPayload.preview_asset];
    }
    return dedupeImageAssets(
        (typedPayload.assets || []).filter((asset) =>
            asset.mime_type.startsWith("image/") &&
            Boolean(asset.asset_url) &&
            ["render_export", "render_preview", "ai_image"].includes(asset.asset_role),
        ),
    );
}

function resolveGenerationDecision(payload: ChatAssistantStructuredPayload | Record<string, unknown> | undefined) {
    if (!payload || Array.isArray(payload)) {
        return null;
    }
    const typedPayload = payload as ChatAssistantStructuredPayload;
    const rendererMetadata =
        typedPayload.renderer_metadata && typeof typedPayload.renderer_metadata === "object"
            ? (typedPayload.renderer_metadata as Record<string, unknown>)
            : null;
    return coerceGenerationDecision(typedPayload.generation_decision || rendererMetadata?.layout_decision);
}

function assetPreviewLabel(asset: KnowledgeAssetResponse) {
    return asset.name || asset.original_filename;
}

function toRecord(value: unknown): Record<string, unknown> {
    return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function readStringArray(value: unknown) {
    if (!Array.isArray(value)) {
        return [];
    }
    return value.map((item) => String(item)).filter(Boolean);
}

function resolveBrandAudienceOptions(context: Record<string, unknown>) {
    const identity = toRecord(context.identity);
    const personas = toRecord(context.personas);
    const primaryPersona = Array.isArray(personas.personas)
        ? toRecord(personas.personas.find((item) => toRecord(item).is_default) || personas.personas[0])
        : {};
    const contentBehavior = toRecord(primaryPersona.content_behavior);
    const selectedAudiences = [
        ...readStringArray(contentBehavior.selected_audiences),
        ...readStringArray(identity.audience_type),
        ...(typeof identity.audience_type === "string" ? [identity.audience_type] : []),
    ];
    const uniqueAudiences = Array.from(new Set(selectedAudiences.filter((item) => AUDIENCE_OPTIONS.includes(item))));
    return uniqueAudiences.length ? uniqueAudiences : AUDIENCE_OPTIONS;
}

function getTemplatePreviewUrl(recommendation: TemplateRecommendationResponse) {
    const metadata =
        recommendation.metadata && typeof recommendation.metadata === "object"
            ? (recommendation.metadata as Record<string, unknown>)
            : {};
    const candidates = [
        recommendation.asset_url,
        metadata.asset_url,
        metadata.preview_asset_url,
        metadata.template_preview_asset_url,
        metadata.preview_url,
        metadata.thumbnail_url,
    ];
    for (const candidate of candidates) {
        if (typeof candidate === "string" && candidate.trim()) {
            return candidate;
        }
    }
    return undefined;
}

function ActionButton({
    selected,
    onClick,
    icon,
    label,
}: {
    selected: boolean;
    onClick: () => void;
    icon: string;
    label: string;
}) {
    return (
        <Button
            type="button"
            variant={"ghost"}
            onClick={onClick}
            className={`inline-flex h-8 items-center rounded-none gap-2 border px-3 py-5 text-sm font-medium transition ${selected ? "border-primary bg-primary/8 text-primary" : "border-[#D9DDE8] bg-white text-[#121212] hover:border-primary/40"
                }`}
        >
            <Image src={icon} alt={`${label} icon`} width={18} height={18} className="w-auto h-auto" />
            <span>{label}</span>
        </Button>
    );
}

function TemplateRecommendationRail({
    recommendations,
    isLoading,
    selectedTemplateId,
    onSelect,
}: {
    recommendations: TemplateRecommendationResponse[];
    isLoading: boolean;
    selectedTemplateId: string;
    onSelect: (templateId: string) => void;
}) {
    const [previewTemplate, setPreviewTemplate] = useState<TemplateRecommendationResponse | null>(null);
    const [brokenPreviewIds, setBrokenPreviewIds] = useState<Record<string, boolean>>({});

    if (!recommendations.length && !isLoading) {
        return null;
    }

    return (
        <div className="space-y-2 rounded-[24px] border border-[#E8EBF4] bg-white/90 px-3 py-3 shadow-[0_16px_36px_-30px_rgba(15,23,42,0.35)]">
            <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-800">Template Direction</p>
                {isLoading ? (
                    <span className="inline-flex items-center gap-2 text-xs font-medium text-primary">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        Matching templates
                    </span>
                ) : null}
            </div>

            <div className="flex gap-2 overflow-x-auto pb-1">
                <button
                    type="button"
                    onClick={() => onSelect("")}
                    className={`flex min-w-[164px] items-center gap-3 rounded-[18px] border px-3 py-2.5 text-left transition ${!selectedTemplateId
                        ? "border-primary bg-primary/8 text-primary shadow-[0_16px_36px_-30px_rgba(60,47,143,0.55)]"
                        : "border-slate-200 bg-white text-slate-700 hover:border-primary/30"
                        }`}
                >
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-[14px] border border-dashed border-current/25 bg-white/80">
                        <span className="text-[11px] font-semibold uppercase tracking-[0.18em]">Auto</span>
                    </div>
                    <div className="min-w-0 flex-1 space-y-1">
                        <p className="line-clamp-2 text-[12px] font-semibold leading-4 text-current">Let Violyt choose</p>
                        <p className="text-[10px] font-medium text-slate-500">
                            {!selectedTemplateId ? "Currently active" : "Switch to auto"}
                        </p>
                    </div>
                </button>
                {recommendations.map((recommendation) => {
                    const selected = recommendation.template_id === selectedTemplateId;
                    const previewUrl = brokenPreviewIds[recommendation.template_id]
                        ? undefined
                        : getTemplatePreviewUrl(recommendation);
                    return (
                        <div
                            key={recommendation.template_id}
                            className={`flex min-w-[172px] items-center gap-2 rounded-[18px] border px-2.5 py-2.5 ${selected
                                ? "border-primary bg-primary/8 shadow-[0_16px_36px_-30px_rgba(60,47,143,0.55)]"
                                : "border-slate-200 bg-white"
                                }`}
                        >
                            <button
                                type="button"
                                onClick={() => previewUrl && setPreviewTemplate(recommendation)}
                                disabled={!previewUrl}
                                className={`flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-[14px] border ${previewUrl
                                    ? "border-slate-200 bg-slate-50 hover:border-primary/30"
                                    : "border-dashed border-slate-200 bg-slate-50 text-slate-400"
                                    }`}
                            >
                                {previewUrl ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img
                                        src={previewUrl}
                                        alt={recommendation.name}
                                        loading="lazy"
                                        onError={() =>
                                            setBrokenPreviewIds((current) => ({
                                                ...current,
                                                [recommendation.template_id]: true,
                                            }))}
                                        className="h-full w-full object-cover"
                                    />
                                ) : (
                                    <span className="px-1 text-center text-[9px] font-medium">No preview</span>
                                )}
                            </button>
                            <div className="min-w-0 flex-1 space-y-1">
                                <p className="line-clamp-2 text-[11px] font-semibold leading-4 text-slate-800">{recommendation.name}</p>
                                {/*
                  {formatRecommendationMatchType(recommendation.match_type)} · {getRecommendationConfidence(recommendation)}
                */}
                                <p className="text-[10px] font-medium text-slate-500">{getRecommendationConfidence(recommendation)}</p>
                            </div>
                            <div className="flex shrink-0 items-center gap-2">
                                <button
                                    type="button"
                                    onClick={() => onSelect(selected ? "" : recommendation.template_id)}
                                    className={`rounded-full border px-2.5 py-1.5 text-[11px] font-medium ${selected
                                        ? "border-primary bg-primary text-white"
                                        : "border-slate-200 bg-white text-slate-700"
                                        }`}
                                >
                                    {selected ? "Pinned" : "Use"}
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>

            <Dialog open={Boolean(previewTemplate)} onOpenChange={(open) => !open && setPreviewTemplate(null)}>
                <DialogContent className="max-w-3xl border-none bg-white p-0">
                    <DialogHeader className="px-6 pb-0 pt-6">
                        <DialogTitle>{previewTemplate?.name || "Template preview"}</DialogTitle>
                    </DialogHeader>
                    <div className="px-6 pb-6 pt-4">
                        {previewTemplate && getTemplatePreviewUrl(previewTemplate) ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                                src={getTemplatePreviewUrl(previewTemplate)}
                                alt={previewTemplate.name}
                                className="max-h-[72vh] w-full rounded-[20px] object-contain"
                            />
                        ) : (
                            <div className="flex min-h-80 items-center justify-center rounded-[20px] border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-500">
                                Preview unavailable
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function GenerationPreviewPlaceholder({
    width,
    height,
}: {
    width?: number;
    height?: number;
}) {
    const safeWidth = Math.max(width || 1080, 1);
    const safeHeight = Math.max(height || 1080, 1);
    const aspectRatio = `${safeWidth} / ${safeHeight}`;
    return (
        <div className="overflow-hidden rounded-[24px] border border-[#E8EBF4] bg-white">
            <div
                className="relative w-full overflow-hidden"
                style={{ aspectRatio }}
            >
                <div className="absolute inset-0 bg-[linear-gradient(135deg,#F8FAFF_0%,#FFFFFF_48%,#F4F7FD_100%)]" />
                <div className="absolute -left-10 top-8 h-40 w-40 rounded-full bg-primary/10 blur-3xl" />
                <div className="absolute -right-8 bottom-8 h-44 w-44 rounded-full bg-emerald-400/15 blur-3xl" />
                <div className="absolute inset-0 animate-pulse">
                    <div className="absolute left-[8%] top-[10%] h-[14%] w-[52%] rounded-[26px] bg-white/80 shadow-[0_20px_50px_-34px_rgba(15,23,42,0.3)]" />
                    <div className="absolute left-[8%] top-[28%] h-[10%] w-[38%] rounded-[22px] bg-slate-100/90" />
                    <div className="absolute right-[8%] top-[18%] h-[36%] w-[32%] rounded-[28px] bg-primary/10" />
                    <div className="absolute left-[8%] bottom-[18%] h-[11%] w-[58%] rounded-[24px] bg-emerald-400/15" />
                    <div className="absolute right-[8%] bottom-[14%] h-[16%] w-[22%] rounded-[28px] bg-white/80 shadow-[0_20px_50px_-34px_rgba(15,23,42,0.3)]" />
                </div>
                <div className="absolute inset-y-0 left-0 w-full animate-pulse bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.38),transparent)]" />
            </div>
        </div>
    );
}

function GenerationDecisionCard({ decision }: { decision: GenerationDecision | null }) {
    const templateLabel = getGenerationDecisionTemplate(decision);
    const templatePreview = getGenerationDecisionTemplatePreview(decision);
    const templateConfidence = getGenerationDecisionConfidence(decision);
    const reasons = getGenerationDecisionReasons(decision);
    const [isPreviewOpen, setIsPreviewOpen] = useState(false);
    if (!decision?.mode && !templateLabel && !reasons.length) {
        return null;
    }

    return (
        <div className="mt-3 rounded-[18px] border border-slate-200 bg-slate-50/90 px-4 py-3 text-sm text-slate-700">
            <div className="flex flex-wrap items-start gap-3">
                <span className="rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                    {formatGenerationMode(decision?.mode)}
                </span>
                {templateLabel ? (
                    <div className="flex items-start gap-3">
                        {templatePreview ? (
                            <button
                                type="button"
                                onClick={() => setIsPreviewOpen(true)}
                                className="overflow-hidden rounded-[12px] border border-slate-200 bg-white"
                            >
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img src={templatePreview} alt={templateLabel} className="h-8 w-8 object-cover" />
                            </button>
                        ) : null}
                        <div className="min-w-0">
                            <p className="line-clamp-2 text-xs font-medium text-slate-600">{templateLabel}</p>
                            {templateConfidence ? <p className="mt-1 text-[11px] text-slate-500">{templateConfidence}</p> : null}
                        </div>
                    </div>
                ) : null}
            </div>
            {reasons.length ? <p className="mt-2 leading-6 text-slate-600">{reasons[0]}</p> : null}
            <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
                <DialogContent className="max-w-3xl border-none bg-white p-0">
                    <DialogHeader className="px-6 pb-0 pt-6">
                        <DialogTitle>{templateLabel || "Template preview"}</DialogTitle>
                    </DialogHeader>
                    <div className="px-6 pb-6 pt-4">
                        {templatePreview ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={templatePreview} alt={templateLabel || "Template preview"} className="max-h-[72vh] w-full rounded-[20px] object-contain" />
                        ) : (
                            <div className="flex min-h-[320px] items-center justify-center rounded-[20px] border border-dashed border-slate-200 bg-slate-50 text-sm text-slate-500">
                                Preview unavailable
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function GeneratedImageViewer({ assets }: { assets: AssetReference[] }) {
    const [activeIndex, setActiveIndex] = useState(0);
    const imageAssets = assets
        .map((asset) => ({ ...asset, resolvedUrl: asset.asset_url || "" }))
        .filter((asset) => Boolean(asset.resolvedUrl));
    const activeAsset = imageAssets[Math.min(activeIndex, Math.max(imageAssets.length - 1, 0))];

    if (!activeAsset) {
        return null;
    }

    const handleSave = () => {
        window.open(activeAsset.resolvedUrl, "_blank", "noopener,noreferrer");
    };

    const handleShare = async () => {
        if (navigator.share) {
            await navigator.share({ title: "Generated image", url: activeAsset.resolvedUrl });
            return;
        }
        await navigator.clipboard.writeText(activeAsset.resolvedUrl);
    };

    return (
        <div className="mt-3 w-full max-w-[520px] bg-[#F4F5F8] px-3 py-3">
            <div className="mb-3 flex items-center justify-between gap-3">
                <span className="text-[12px] font-medium text-[#333333]">Generated image</span>
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        onClick={handleSave}
                        className="inline-flex h-7 items-center gap-1.5 border border-primary bg-white px-2.5 text-[11px] font-medium text-primary"
                    >
                        <Download className="h-3.5 w-3.5" />
                        <span>Save</span>
                    </button>
                    <button
                        type="button"
                        onClick={() => void handleShare()}
                        className="inline-flex h-7 items-center gap-1.5 bg-primary px-2.5 text-[11px] font-medium text-white"
                    >
                        <Share2 className="h-3.5 w-3.5" />
                        <span>Share</span>
                    </button>
                </div>
            </div>
            <div className="flex items-center gap-4">
                <div className="flex min-h-[220px] flex-1 items-center justify-center bg-[#EEF0F5] p-4">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={activeAsset.resolvedUrl} alt="Generated image" className="max-h-[360px] w-auto max-w-full object-contain" />
                </div>
                {imageAssets.length > 1 ? (
                    <div className="flex max-h-[320px] w-[78px] shrink-0 flex-col gap-3 overflow-y-auto pr-1">
                        {imageAssets.map((asset, index) => (
                            <button
                                key={asset.asset_id || asset.storage_path || asset.asset_url || index}
                                type="button"
                                onClick={() => setActiveIndex(index)}
                                className={`border bg-white p-1 transition ${index === activeIndex ? "border-primary" : "border-transparent hover:border-[#D9DDE8]"
                                    }`}
                            >
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img src={asset.resolvedUrl} alt={`Generated image ${index + 1}`} className="h-14 w-full object-cover" />
                            </button>
                        ))}
                    </div>
                ) : null}
            </div>
        </div>
    );
}

function CampaignGoalMultiSelect({
    value,
    onChange,
}: {
    value: string;
    onChange: (value: string) => void;
}) {
    const [isOpen, setIsOpen] = useState(false);
    const selectedValues = useMemo(
        () => value.split(",").map((item) => item.trim()).filter(Boolean),
        [value],
    );

    const toggleGoal = (goal: string) => {
        const nextValues = selectedValues.includes(goal)
            ? selectedValues.filter((item) => item !== goal)
            : [...selectedValues, goal];
        onChange(nextValues.join(", "));
    };

    return (
        <div className="relative">
            <button
                type="button"
                onClick={() => setIsOpen((current) => !current)}
                className="flex h-12 w-full items-center justify-between rounded-xl bg-input-field px-4 text-left text-sm text-[#8B8B94]"
            >
                <span className="truncate">{selectedValues.length ? selectedValues.join(", ") : "Select"}</span>
                <ChevronDown className="h-4 w-4 shrink-0 text-[#8B8B94]" />
            </button>
            {isOpen ? (
                <div className="absolute left-0 right-0 z-20 max-h-72 overflow-y-auto rounded-b-xl border border-t-0 border-[#ECEEF5] bg-white shadow-[0_12px_24px_-18px_rgba(15,23,42,0.35)] thin-scrollbar">
                    {campaignGoalOptions.map((goal) => (
                        <label
                            key={goal}
                            className="flex cursor-pointer items-center gap-4 border-b border-[#F0F1F5] px-4 py-3 text-sm text-[#121212] last:border-b-0"
                        >
                            <input
                                type="checkbox"
                                checked={selectedValues.includes(goal)}
                                onChange={() => toggleGoal(goal)}
                                className="h-4 w-4 rounded border-[#8D8D95] accent-[#121212]"
                            />
                            <span>{goal}</span>
                        </label>
                    ))}
                </div>
            ) : null}
        </div>
    );
}

function StudioPanel({
    platform,
    setPlatform,
    format,
    setFormat,
    fileType,
    setFileType,
    sizeLabel,
    setSizeLabel,
    campaignGoal,
    setCampaignGoal,
    onToggle,
    className,
}: {
    platform: Platform;
    setPlatform: (value: Platform) => void;
    format: FormatMode;
    setFormat: (value: FormatMode) => void;
    fileType: FileType;
    setFileType: (value: FileType) => void;
    sizeLabel: string;
    setSizeLabel: (value: string) => void;
    campaignGoal: string;
    setCampaignGoal: (value: string) => void;
    onToggle?: () => void;
    className?: string;
}) {
    const sizeOptions = resolveSizeOptions(format, platform);

    const applyFormat = (next: FormatMode) => {
        if (next === "video") return;
        setFormat(next);
        setSizeLabel(resolveSizeOptions(next, platform)[0].label);
    };

    const applyPlatform = (next: Platform) => {
        setPlatform(next);
        setSizeLabel(resolveSizeOptions(format, next)[0].label);
    };

    return (
        <aside className={`w-full relative min-h-[calc(100vh-64px)] overflow-y-auto space-y-6 border-l border-[#E5E7F0] bg-white px-5 ${className || ""} thin-scrollbar`}>
            {/* Header */}
            <div className="sticky top-0 flex items-center justify-between py-5 bg-white z-10">
                <h3 className="text-lg font-bold text-[#121212]">Studio</h3>
                <Button
                    type="button"
                    variant={"ghost"}
                    onClick={onToggle}
                    className={`flex h-10 w-10 items-center justify-center text-[#121212]`}
                >
                    <Image src="/actions_icons/toggle.svg" alt="Close panel" width={16} height={16} className="h-4 w-4" />
                </Button>
            </div>

            <div className="space-y-3">
                <p className="text-base font-medium text-[#121212]">Format</p>
                <div className="grid grid-cols-2 gap-2">
                    {formatOptions.map((option) => (
                        <Button
                            variant={"ghost"}
                            key={option.value}
                            type="button"
                            disabled={!option.enabled}
                            onClick={() => option.enabled && applyFormat(option.value)}
                            className={`min-w-0 rounded-none p-6 text-center text-sm font-medium ${format === option.value
                                ? "bg-[#EBEBEB] text-[#121212]"
                                : option.enabled
                                    ? "bg-[#F9F9F9] text-[#8D8D95]"
                                    : "cursor-not-allowed bg-[#FAFAFB] text-[#B8B8BE]"
                                }`}
                        >
                            {option.label}
                        </Button>
                    ))}
                </div>
            </div>

            <div className="space-y-3">
                <p className="text-base font-medium text-[#121212]">Platform</p>
                <div className="flex gap-1 border-b border-[#D1D3DA]">
                    {platformOptions.map((option) => (
                        <Button
                            variant={"ghost"}
                            key={option}
                            onClick={() => applyPlatform(option)}
                            className={`flex flex-1 rounded-none border-b-2 p-5 text-base font-normal ${platform === option ? "border-b-primary text-[#121212]" : "border-transparent text-[#393939]"
                                }`}
                        >
                            <span className="block truncate">{platformLabels[option]}</span>
                        </Button>
                    ))}
                </div>
                <p className="text-sm font-medium text-[#121212]">Size</p>
                <div className="grid grid-cols-1 gap-2">
                    {sizeOptions.map((option) => (
                        <Button
                            variant={"ghost"}
                            key={option.label}
                            type="button"
                            onClick={() => setSizeLabel(option.label)}
                            className={`p-4 rounded-none text-left text-sm font-medium text-[#919191] ${sizeLabel === option.label ? "bg-[#EBEBEB] text-[#121212]" : "bg-[#F9F9F9]"
                                }`}
                        >
                            {option.label}
                        </Button>
                    ))}
                </div>
            </div>

            <div className="space-y-3">
                <p className="text-base font-medium text-[#121212]">File Type</p>
                <div className="grid grid-cols-2 gap-2">
                    {fileTypeOptions.map((option) => (
                        <Button
                            variant={"ghost"}
                            key={option}
                            type="button"
                            onClick={() => setFileType(option)}
                            className={`p-6 text-[#919191] rounded-none text-center text-sm font-medium uppercase ${fileType === option ? "bg-[#EBEBEB]" : "bg-[#F9F9F9]"
                                }`}
                        >
                            {option}
                        </Button>
                    ))}
                </div>
            </div>

            <div className="space-y-3">
                <FormField label="Campaign Goal">
                    <CampaignGoalMultiSelect
                        value={campaignGoal}
                        onChange={setCampaignGoal}
                    />
                </FormField>
            </div>
        </aside>
    );
}

export default function WorkspaceChat({ brandKey }: WorkspaceChatProps) {
    const searchParams = useSearchParams();
    const { data: brands, isLoading: isBrandsLoading } = useBrands();
    const brand = useMemo(() => resolveBrandByRouteKey(brands, brandKey), [brands, brandKey]);
    const brandId = brand?.id || "";
    const { data: brandUsage } = useBrandUsage(brandId);
    const targetAudienceOptions = useMemo(
        () => resolveBrandAudienceOptions(brand?.resolved_brand_context || {}),
        [brand?.resolved_brand_context],
    );

    const { data: sessions } = useChatSessions(brandId);
    const createSession = useCreateChatSession(brandId);
    const uploadKnowledgeAsset = useUploadKnowledgeAsset(brandId);
    const [activeSessionId, setActiveSessionId] = useState("");
    const selectedSessionId = searchParams.get("chat") || "";
    const selectedSessionIsAvailable = Boolean(
        selectedSessionId && sessions?.some((session) => session.id === selectedSessionId),
    );
    const resolvedActiveSessionId = selectedSessionIsAvailable
        ? selectedSessionId
        : activeSessionId || sessions?.[0]?.id || "";
    const {
        data: messages,
        fetchNextPage: fetchOlderMessages,
        hasNextPage: hasOlderMessages,
        isFetchingNextPage: isFetchingOlderMessages,
    } = useChatMessages(brandId, resolvedActiveSessionId);
    const sendMessage = useSendChatMessage(brandId);
    const cancelChatGeneration = useCancelChatGeneration(brandId);
    const toneCheck = useToneCheck(brandId);
    const { runPipeline, approveBlueprint, rejectBlueprint, isApproving } = usePipeline();

    const [pipelineUi, setPipelineUi] = useState<ChatPipelineState>({ status: "idle" });

    const [selectedAction, setSelectedAction] = useState<ActionMode>("none");
    const [workspacePrompt, setWorkspacePrompt] = useState("");
    const [campaignFocus, setCampaignFocus] = useState("");
    const [campaignAudience, setCampaignAudience] = useState("");
    const [campaignObjective, setCampaignObjective] = useState("");
    const [socialTopic, setSocialTopic] = useState("");
    const [socialGoal, setSocialGoal] = useState("");
    const [repurposeSource, setRepurposeSource] = useState("");
    const [repurposeTarget, setRepurposeTarget] = useState("");
    const [alignmentContent, setAlignmentContent] = useState("");
    const [composerDraft, setComposerDraft] = useState("");
    const [studioPlatform, setStudioPlatform] = useState<Platform>("linkedin");
    const [actionPlatform, setActionPlatform] = useState<Platform | "">("");
    const [studioFormat, setStudioFormat] = useState<FormatMode>("static");
    const [studioFileType, setStudioFileType] = useState<FileType>("png");
    const [studioSizeLabel, setStudioSizeLabel] = useState("1.91:1 · 1200×627");
    const [campaignGoal, setCampaignGoal] = useState("");
    const [attachedAssets, setAttachedAssets] = useState<KnowledgeAssetResponse[]>([]);
    const [selectedTemplateId, setSelectedTemplateId] = useState("");
    const [selectedTemplateName, setSelectedTemplateName] = useState("");
    const [attachmentError, setAttachmentError] = useState("");
    const [workspaceError, setWorkspaceError] = useState("");
    const [isStudioOpen, setIsStudioOpen] = useState(true);
    const [chatSearchQuery, setChatSearchQuery] = useState("");
    const [activeChatSearchMatchIndex, setActiveChatSearchMatchIndex] = useState(0);
    const attachmentInputRef = useRef<HTMLInputElement | null>(null);
    const composerTextareaRef = useRef<HTMLTextAreaElement | null>(null);
    const promptTextareaRef = useRef<HTMLTextAreaElement | null>(null);
    const messageListRef = useRef<HTMLDivElement | null>(null);
    const messageBottomRef = useRef<HTMLDivElement | null>(null);
    const messageElementRefs = useRef(new Map<string, HTMLDivElement>());
    const activeGenerationControllerRef = useRef<AbortController | null>(null);
    const activeGenerationSessionRef = useRef<string>("");
    const pipelineInFlightRef = useRef(false);

    const sizeOption = useMemo(() => {
        const options = resolveSizeOptions(studioFormat, studioPlatform);
        return options.find((entry) => entry.label === studioSizeLabel) || options[0];
    }, [studioFormat, studioPlatform, studioSizeLabel]);
    const studioPanel = useMemo<StudioPanelSelection>(
        () => ({
            format: studioFormat === "video" ? "static" : studioFormat,
            platform_preset: studioPlatform,
            file_type: studioFileType,
            size: { width: sizeOption.width, height: sizeOption.height },
        }),
        [sizeOption.height, sizeOption.width, studioFileType, studioFormat, studioPlatform],
    );
    const brandLifecycle = brand?.lifecycle_state || "draft";
    const canGenerateInWorkspace = true;
    const pipelineBusy =
        pipelineUi.status === "running" ||
        pipelineUi.status === "generating" ||
        runPipeline.isPending ||
        approveBlueprint.isPending;
    const isGeneratingMessage = createSession.isPending || sendMessage.isPending || pipelineBusy;
    const recommendationPrompt = useMemo(() => {
        if (selectedAction === "idea") {
            return [campaignFocus, campaignAudience, campaignObjective || campaignGoal, workspacePrompt]
                .map((item) => item.trim())
                .filter(Boolean)
                .join("\n");
        }
        if (selectedAction === "social") {
            return [workspacePrompt, socialTopic || campaignGoal].map((item) => item.trim()).filter(Boolean).join("\n");
        }
        if (selectedAction === "repurpose") {
            return [repurposeSource, repurposeTarget, workspacePrompt].map((item) => item.trim()).filter(Boolean).join("\n");
        }
        if (selectedAction === "alignment") {
            return alignmentContent.trim();
        }
        return composerDraft.trim() || workspacePrompt.trim();
    }, [
        alignmentContent,
        campaignAudience,
        campaignFocus,
        campaignGoal,
        campaignObjective,
        composerDraft,
        repurposeSource,
        repurposeTarget,
        selectedAction,
        socialGoal,
        workspacePrompt,
    ]);
    const debouncedRecommendationPrompt = useDebouncedValue(recommendationPrompt, 400);
    const { data: templateRecommendations = [], isFetching: isFetchingTemplateRecommendations } = useTemplateRecommendations(
        brandId,
        debouncedRecommendationPrompt,
        studioPanel,
        3,
        canGenerateInWorkspace &&
        !isGeneratingMessage &&
        debouncedRecommendationPrompt.trim().length >= 12,
    );
    const selectedTemplate = useMemo(
        () => templateRecommendations.find((item) => item.template_id === selectedTemplateId) || null,
        [selectedTemplateId, templateRecommendations],
    );
    const selectedTemplateLabel = selectedTemplate?.name || selectedTemplateName;
    const hasConversation =
        Boolean((messages || []).length) ||
        (pipelineUi.status !== "idle" && pipelineUi.status !== "cancelled");
    const allocationPercent = brandUsage?.capacity_percent ?? 0;
    const usedWithinAllocationPercent = brandUsage?.usage_percent ?? 0;
    const usageRemainingPercent = Math.max(
        0,
        Math.min(100, Math.round((allocationPercent * (100 - usedWithinAllocationPercent)) / 100)),
    );
    const usagePendingLabel = `${brand?.name ?? "Brand"} Usage Pending: ${usageRemainingPercent}%`;
    const freshChatHistory = useMemo(
        () =>
            [...(sessions || [])]
                .filter((session) => session.id !== resolvedActiveSessionId || session.title?.trim())
                .sort((left: ChatSessionResponse, right: ChatSessionResponse) =>
                    new Date(right.updated_at || right.created_at).getTime() - new Date(left.updated_at || left.created_at).getTime(),
                )
                .slice(0, 8),
        [resolvedActiveSessionId, sessions],
    );
    const activeActionOption = selectedAction === "none" ? null : actionOptionById[selectedAction];
    const orderedMessages = useMemo(
        () =>
            [...(messages || [])].sort((left: ChatMessageResponse, right: ChatMessageResponse) => {
                const createdDelta = new Date(left.created_at).getTime() - new Date(right.created_at).getTime();
                if (createdDelta !== 0) {
                    return createdDelta;
                }
                if (left.role !== right.role) {
                    return left.role === "user" ? -1 : 1;
                }
                return left.id.localeCompare(right.id);
            }),
        [messages],
    );
    const normalizedChatSearchQuery = chatSearchQuery.trim().toLowerCase();
    const chatSearchMatches = useMemo(() => {
        if (!normalizedChatSearchQuery) {
            return [];
        }
        return orderedMessages.flatMap((message) =>
            Array.from({ length: countSearchOccurrences(message.message_text, normalizedChatSearchQuery) }, (_, occurrenceIndex) => ({
                messageId: message.id,
                occurrenceIndex,
            })),
        );
    }, [normalizedChatSearchQuery, orderedMessages]);
    const activeChatSearchMatch = chatSearchMatches[activeChatSearchMatchIndex] || null;
    const activeChatSearchMatchId = activeChatSearchMatch?.messageId || "";
    const latestMessageId = orderedMessages[orderedMessages.length - 1]?.id || "";
    const [generationProgressIndex, setGenerationProgressIndex] = useState(0);
    const activeGenerationMessage = isGeneratingMessage
        ? GENERATION_PROGRESS_MESSAGES[generationProgressIndex] || GENERATION_PROGRESS_MESSAGES[0]
        : GENERATION_PROGRESS_MESSAGES[0];
    const activeGenerationStatusLine = formatGenerationStatusLine(activeGenerationMessage);

    useEffect(() => {
        if (!isGeneratingMessage) {
            return;
        }

        const startedAt = Date.now();
        const updateProgress = () => {
            const elapsedMs = Date.now() - startedAt;
            const nextIndex = Math.floor(elapsedMs / 3000) % GENERATION_PROGRESS_MESSAGES.length;
            setGenerationProgressIndex(nextIndex);
        };

        updateProgress();
        const interval = window.setInterval(updateProgress, 900);
        return () => window.clearInterval(interval);
    }, [isGeneratingMessage]);

    const handleTemplateSelection = (templateId: string) => {
        setSelectedTemplateId(templateId);
        if (!templateId) {
            setSelectedTemplateName("");
            return;
        }
        const matchedTemplate = templateRecommendations.find((item) => item.template_id === templateId);
        if (matchedTemplate?.name) {
            setSelectedTemplateName(matchedTemplate.name);
        }
    };

    useEffect(() => {
        if (!sessions?.length) {
            return;
        }

        if (!selectedSessionId || !selectedSessionIsAvailable) {
            setActiveSessionId("");
            return;
        }

        if (activeSessionId !== selectedSessionId) {
            setActiveSessionId(selectedSessionId);
        }
    }, [activeSessionId, selectedSessionId, selectedSessionIsAvailable, sessions]);

    useEffect(() => {
        if (!resolvedActiveSessionId || !hasOlderMessages || isFetchingOlderMessages) {
            return;
        }
        const timeoutId = window.setTimeout(() => {
            void fetchOlderMessages();
        }, 250);
        return () => window.clearTimeout(timeoutId);
    }, [fetchOlderMessages, hasOlderMessages, isFetchingOlderMessages, resolvedActiveSessionId]);

    useEffect(() => {
        setActiveChatSearchMatchIndex(0);
    }, [normalizedChatSearchQuery]);

    useEffect(() => {
        if (!chatSearchMatches.length) {
            setActiveChatSearchMatchIndex(0);
            return;
        }
        setActiveChatSearchMatchIndex((current) => Math.min(current, chatSearchMatches.length - 1));
    }, [chatSearchMatches.length]);

    useEffect(() => {
        if (!activeChatSearchMatchId) {
            return;
        }
        const timeoutId = window.setTimeout(() => {
            messageElementRefs.current.get(activeChatSearchMatchId)?.scrollIntoView({
                behavior: "smooth",
                block: "center",
            });
        }, 80);
        return () => window.clearTimeout(timeoutId);
    }, [activeChatSearchMatchId, chatSearchQuery]);

    useEffect(() => {
        if (!resolvedActiveSessionId || !orderedMessages.length || normalizedChatSearchQuery) {
            return;
        }
        const timeoutId = window.setTimeout(() => {
            const messageList = messageListRef.current;
            if (messageList) {
                messageList.scrollTop = messageList.scrollHeight;
                return;
            }
            messageBottomRef.current?.scrollIntoView({ block: "end" });
        }, 80);
        return () => window.clearTimeout(timeoutId);
    }, [isGeneratingMessage, latestMessageId, normalizedChatSearchQuery, orderedMessages.length, resolvedActiveSessionId]);

    useEffect(() => {
        resizeComposer(composerTextareaRef.current);
    }, [composerDraft]);

    useEffect(() => {
        resizeComposer(promptTextareaRef.current);
    }, [workspacePrompt]);

    if (isBrandsLoading) {
        return <div className="p-5 text-sm text-slate-500">Loading workspace...</div>;
    }

    if (!brand) {
        return <div className="p-5 text-sm text-slate-500">Brand Space not found.</div>;
    }

    const extractApiError = (error: unknown, fallback: string) => {
        if (axios.isAxiosError(error)) {
            if (error.code === "ECONNABORTED" || /timeout/i.test(String(error.message || ""))) {
                return "Timed out waiting for the pipeline (10 min). Content prep + image gen can take a few minutes — try again once.";
            }
            return String(error.response?.data?.detail || error.response?.data?.message || error.message || fallback);
        }
        if (error instanceof Error) {
            return error.message;
        }
        return fallback;
    };

    const isRequestCanceled = (error: unknown) =>
        axios.isCancel(error) || (axios.isAxiosError(error) && error.code === "ERR_CANCELED");

    const ensureSession = async () => {
        if (!canGenerateInWorkspace) {
            throw new Error("This Brand Space is still in draft. Activate it before generating content or images.");
        }
        if (resolvedActiveSessionId) {
            return resolvedActiveSessionId;
        }
        const session = await createSession.mutateAsync({
            title: workspacePrompt || `${brand.name} Workspace`,
            studio_panel: studioPanel,
        });
        setActiveSessionId(session.id);
        return session.id;
    };

    const cancelActiveGeneration = () => {
        const sessionId = activeGenerationSessionRef.current || resolvedActiveSessionId;
        activeGenerationControllerRef.current?.abort();
        activeGenerationControllerRef.current = null;
        activeGenerationSessionRef.current = "";
        if (sessionId) {
            cancelChatGeneration.mutate(sessionId);
        }
    };

    const dispatchGeneration = async (message: string) => {
        if (
            pipelineInFlightRef.current ||
            isGeneratingMessage ||
            runPipeline.isPending ||
            approveBlueprint.isPending
        ) {
            return;
        }
        if (!message.trim()) {
            setWorkspaceError("Enter a prompt before sending.");
            return;
        }
        pipelineInFlightRef.current = true;
        try {
            setWorkspaceError("");
            setGenerationProgressIndex(0);
            await ensureSession();

            // Creative formats use Violyt Intelligence Pipeline in chat (blueprint → AI-baked text image).
            if (studioFormat !== "video") {
                const pipelinePlatform =
                    studioPlatform === "x" ? "twitter" : studioPlatform === "youtube_thumbnail" ? "linkedin" : studioPlatform;
                const pipelineFormat =
                    studioFormat === "carousel" || studioFormat === "infographic" ? studioFormat : "static";

                setPipelineUi({
                    status: "running",
                    prompt: message.trim(),
                    format: pipelineFormat,
                    blueprint: null,
                    imageUrls: [],
                    error: null,
                });
                setSelectedAction("none");
                setComposerDraft("");
                setWorkspacePrompt((current) => (current.trim() === message.trim() ? "" : current));
                setAttachedAssets([]);
                setAttachmentError("");

                const phase1 = await runPipeline.mutateAsync({
                    brand_id: brandId,
                    user_prompt: message.trim(),
                    platform: pipelinePlatform as "linkedin" | "instagram" | "twitter",
                    format: pipelineFormat,
                });

                if (phase1.status === "awaiting_blueprint_approval" && phase1.creative_blueprint) {
                    setPipelineUi({
                        status: "awaiting_blueprint_approval",
                        runId: phase1.run_id || undefined,
                        prompt: message.trim(),
                        format: pipelineFormat,
                        blueprint: phase1.creative_blueprint,
                        imageUrls: [],
                        error: null,
                    });
                    return;
                }

                if (phase1.status === "failed") {
                    setPipelineUi({
                        status: "failed",
                        prompt: message.trim(),
                        format: pipelineFormat,
                        error: phase1.error || "Pipeline failed before blueprint approval.",
                    });
                    return;
                }

                // Unexpected complete without approve gate — still show images if present
                const urls =
                    phase1.final_output?.asset_urls?.filter(Boolean) ||
                    (phase1.final_output?.asset_url ? [phase1.final_output.asset_url] : []);
                setPipelineUi({
                    status: urls.length ? "complete" : "failed",
                    runId: phase1.run_id || undefined,
                    prompt: message.trim(),
                    format: pipelineFormat,
                    blueprint: phase1.creative_blueprint,
                    imageUrls: urls,
                    error: urls.length ? null : "No image returned from pipeline.",
                });
                return;
            }

            const sessionId = await ensureSession();
            const controller = new AbortController();
            activeGenerationControllerRef.current = controller;
            activeGenerationSessionRef.current = sessionId;
            await sendMessage.mutateAsync({
                sessionId,
                data: {
                    message,
                    studio_panel: studioPanel,
                    generate_image: false,
                    template_id: selectedTemplateId || undefined,
                    reference_asset_ids: attachedAssets.map((asset) => asset.id),
                },
                signal: controller.signal,
            });
            setSelectedAction("none");
            setComposerDraft("");
            setWorkspacePrompt((current) => (current.trim() === message.trim() ? "" : current));
            setAttachedAssets([]);
            setAttachmentError("");
        } catch (error) {
            if (isRequestCanceled(error)) {
                return;
            }
            const detail = extractApiError(error, "Unable to start generation right now.");
            setWorkspaceError(detail);
            setPipelineUi((current) =>
                current.status === "running" || current.status === "generating"
                    ? { ...current, status: "failed", error: detail }
                    : current,
            );
        } finally {
            pipelineInFlightRef.current = false;
            activeGenerationControllerRef.current = null;
            activeGenerationSessionRef.current = "";
        }
    };

    const handleApproveBlueprint = async (edited: CreativeBlueprintResponse) => {
        if (!pipelineUi.runId) return;
        try {
            setPipelineUi((current) => ({ ...current, status: "generating", blueprint: edited, error: null }));
            const phase2 = await approveBlueprint.mutateAsync({
                run_id: pipelineUi.runId,
                creative_blueprint: edited,
            });
            const urls =
                phase2.final_output?.asset_urls?.filter(Boolean) ||
                (phase2.final_output?.asset_url ? [phase2.final_output.asset_url] : []);
            if (phase2.status === "failed" || !urls.length) {
                setPipelineUi((current) => ({
                    ...current,
                    status: "failed",
                    error: phase2.error || "Image generation failed after approval.",
                }));
                return;
            }
            setPipelineUi((current) => ({
                ...current,
                status: "complete",
                blueprint: phase2.creative_blueprint || edited,
                imageUrls: urls,
                error: null,
            }));
        } catch (error) {
            const detail = extractApiError(
                error,
                "Could not approve blueprint. If the server restarted mid-run, start a new prompt.",
            );
            setPipelineUi((current) => ({
                ...current,
                status: "failed",
                error: detail,
            }));
            setWorkspaceError(detail);
        }
    };

    const handleCancelBlueprint = async () => {
        if (pipelineUi.runId) {
            try {
                await rejectBlueprint.mutateAsync({ run_id: pipelineUi.runId });
            } catch {
                // ignore cancel errors
            }
        }
        setPipelineUi({ status: "idle" });
    };

    const handleReferenceUpload = async (files: FileList | null) => {
        if (!files?.length) {
            return;
        }
        try {
            setAttachmentError("");
            const uploaded = await Promise.all(
                Array.from(files).map(async (file) =>
                    uploadKnowledgeAsset.mutateAsync({
                        name: stripFileExtension(file.name),
                        filename: file.name,
                        mime_type: file.type || "application/octet-stream",
                        content_base64: await fileToDataUrl(file),
                        channel: "chat_reference",
                        skip_processing: false,
                        metadata: {
                            asset_role: "chat_reference",
                            section: "workspace_chat",
                            tags: ["Chat Reference"],
                        },
                    }),
                ),
            );
            setAttachedAssets((current) => [...current, ...uploaded]);
        } catch {
            setAttachmentError("Unable to upload reference assets right now.");
        }
    };

    const toggleReferenceAsset = (asset: KnowledgeAssetResponse) => {
        setAttachedAssets((current) =>
            current.some((item) => item.id === asset.id)
                ? current.filter((item) => item.id !== asset.id)
                : [...current, asset],
        );
    };

    const handleActionGenerate = async () => {
        const actionPlatformLabel = actionPlatform ? platformLabels[actionPlatform] : "";
        if (selectedAction === "idea") {
            await dispatchGeneration(
                `Generate campaign ideas.\nCampaign focus: ${campaignFocus}\nTarget audience: ${campaignAudience}\nCampaign objective: ${campaignObjective || campaignGoal}\nPlatform: ${actionPlatformLabel || "Not specified"}\nAdditional context: ${workspacePrompt}`,
            );
            return;
        }
        if (selectedAction === "social") {
            await dispatchGeneration(
                `Create a ${actionPlatformLabel ? `${actionPlatformLabel} ` : ""}social media post.\nGoal: ${socialGoal || campaignGoal}\nTopic: ${workspacePrompt}\nCampaign focus: ${campaignFocus}`,
            );
            return;
        }
        if (selectedAction === "repurpose") {
            await dispatchGeneration(
                `Repurpose the following content.\nSource content: ${repurposeSource}\nTarget outcome: ${repurposeTarget}\nPlatform: ${actionPlatformLabel || "Not specified"}\nAdditional context: ${workspacePrompt}`,
            );
            return;
        }
        if (alignmentContent.trim()) {
            await toneCheck.mutateAsync({ content: alignmentContent });
        }
    };

    const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            void dispatchGeneration(composerDraft);
        }
    };

    const handlePromptKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
            event.preventDefault();
            void dispatchGeneration(workspacePrompt);
        }
    };

    const goToPreviousSearchMatch = () => {
        if (!chatSearchMatches.length) {
            return;
        }
        setActiveChatSearchMatchIndex((current) =>
            current <= 0 ? chatSearchMatches.length - 1 : current - 1,
        );
    };

    const goToNextSearchMatch = () => {
        if (!chatSearchMatches.length) {
            return;
        }
        setActiveChatSearchMatchIndex((current) =>
            current >= chatSearchMatches.length - 1 ? 0 : current + 1,
        );
    };

    return (
        <div className="min-h-[calc(100vh-38px)] bg-white">
            <input
                ref={attachmentInputRef}
                type="file"
                className="hidden"
                multiple
                onChange={(event) => void handleReferenceUpload(event.target.files)}
            />
            <div className="min-h-[calc(100vh-38px)]">
                <div className="h-full">

                    {workspaceError ? (
                        <div className="mx-auto mb-6 max-w-4xl rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                            {workspaceError}
                        </div>
                    ) : null}
                    {hasConversation ? (
                        <div className="flex h-[calc(100vh-32px)] flex-col">
                            <div className={`grid min-h-0 flex-1 ${isStudioOpen ? "xl:grid-cols-[minmax(0,1fr)_296px]" : "xl:grid-cols-1"}`}>


                                <div className="flex min-h-0 flex-col bg-white">
                                    {/* Header */}
                                    <div className="flex h-[61px] py-10 items-center justify-between border-b border-[#E5E5EA] bg-white">
                                        <div className="flex items-center justify-center gap-10 px-3">
                                            {/* <h1 className="font-dmSans text-3xl font-bold text-primary">{brand.name}</h1> */}
                                            <div className="flex gap-2 relative">
                                                <h1 className="font-dmSans text-3xl font-bold text-primary">{brand.name}</h1>
                                                <Link
                                                    href={`/brand_space/${brandId}/edit`}
                                                    className="absolute -right-7 -top-1 text-sm text-[#121212] hover:underline"
                                                >
                                                    <Image src="/actions_icons/chat/redirect_link.svg" alt="Edit icon" width={19} height={19} className="inline-block mr-1" />
                                                </Link>
                                            </div>
                                            <UsageRing
                                                value={usageRemainingPercent}
                                                label={usagePendingLabel}
                                            />
                                        </div>

                                        <div className="flex items-center gap-4">
                                            {hasConversation ? (
                                                <div className={`relative hidden md:block ${isStudioOpen && 'px-6'} `}>
                                                    <Search className={`pointer-events-none absolute ${isStudioOpen ? "left-8" : "left-4"} top-1/2 h-4 w-4 -translate-y-1/2 text-[#77759A]`} />
                                                    <Input
                                                        placeholder="Search"
                                                        value={chatSearchQuery}
                                                        onChange={(event) => setChatSearchQuery(event.target.value)}
                                                        className="h-10 w-68 rounded-none border-[#E1E3EC] bg-blue pl-10 pr-24 text-sm text-[#77759A] shadow-none focus-visible:ring-0"
                                                    />
                                                    {chatSearchQuery.trim() ? (
                                                        <div className={`absolute ${isStudioOpen ? "right-8" : "right-2"} top-1/2 flex -translate-y-1/2 items-center gap-1 text-[11px] text-[#77759A]`}>
                                                            <span className="min-w-8 text-right">
                                                                {chatSearchMatches.length ? activeChatSearchMatchIndex + 1 : 0}/{chatSearchMatches.length}
                                                            </span>
                                                            <button
                                                                type="button"
                                                                onClick={goToPreviousSearchMatch}
                                                                disabled={!chatSearchMatches.length}
                                                                aria-label="Previous search match"
                                                                className="flex h-5 w-5 items-center justify-center text-[#77759A] disabled:opacity-30"
                                                            >
                                                                <ChevronUp className="h-3.5 w-3.5" />
                                                            </button>
                                                            <button
                                                                type="button"
                                                                onClick={goToNextSearchMatch}
                                                                disabled={!chatSearchMatches.length}
                                                                aria-label="Next search match"
                                                                className="flex h-5 w-5 items-center justify-center text-[#77759A] disabled:opacity-30"
                                                            >
                                                                <ChevronDown className="h-3.5 w-3.5" />
                                                            </button>
                                                        </div>
                                                    ) : null}
                                                </div>
                                            ) : null}
                                            {hasConversation ? (
                                                <Button
                                                    type="button"
                                                    variant={"ghost"}
                                                    onClick={() => setIsStudioOpen((current) => !current)}
                                                    className={`flex h-10 w-10 items-center justify-center text-[#121212] ${isStudioOpen && 'hidden'}`}
                                                    aria-label={isStudioOpen ? "Hide Studio" : "Show Studio"}
                                                >
                                                    {!isStudioOpen && <Image src="/toggleSidebar.svg" alt="Close panel" width={16} height={16} className="h-4 w-4" />}
                                                </Button>
                                            ) : null}
                                        </div>
                                    </div>
                                    <div ref={messageListRef} className="flex-1 space-y-8 overflow-y-auto px-1 py-5 thin-scrollbar">
                                        {orderedMessages.map((message) => {
                                            const previewAssets = message.role === "assistant" ? resolveGeneratedImageAssets(message.structured_payload) : [];
                                            const previewUrl = previewAssets[0]?.asset_url || undefined;
                                            const generationDecision = message.role === "assistant" ? resolveGenerationDecision(message.structured_payload) : null;
                                            const imageStatus =
                                                message.role === "assistant" &&
                                                    !previewUrl &&
                                                    (message.structured_payload as ChatAssistantStructuredPayload)?.image_generation_requested
                                                    ? (message.structured_payload as ChatAssistantStructuredPayload).image_generation_status
                                                    : null;
                                            // Hide stale old-chat image failures — pipeline UI owns creative generation now.
                                            const text = String(message.message_text || "");
                                            if (
                                                message.role === "assistant" &&
                                                !previewAssets.length &&
                                                /couldn.?t generate the visual this time/i.test(text)
                                            ) {
                                                return null;
                                            }
                                            return (
                                                <div
                                                    key={message.id}
                                                    ref={(node) => {
                                                        if (node) {
                                                            messageElementRefs.current.set(message.id, node);
                                                        } else {
                                                            messageElementRefs.current.delete(message.id);
                                                        }
                                                    }}
                                                    className={`${isStudioOpen ? "px-3" : "pr-10 pl-3"} ${message.role === "user" ? "ml-auto w-fit max-w-[70%]" : "mr-auto max-w-[78%]"}`}
                                                >
                                                    <div className={`p-3 text-base text-[#353030]  ${message.role === "user"
                                                        ? "bg-[#F4F4F4]"
                                                        : "bg-[#F8F8F8]"
                                                        }`}>
                                                        <p className="whitespace">
                                                            <HighlightedMessageText
                                                                text={message.message_text}
                                                                searchQuery={chatSearchQuery}
                                                                activeOccurrenceIndex={
                                                                    message.id === activeChatSearchMatchId
                                                                        ? activeChatSearchMatch?.occurrenceIndex ?? null
                                                                        : null
                                                                }
                                                            />
                                                        </p>
                                                    </div>
                                                    {message.role === "assistant" ? <GenerationDecisionCard decision={generationDecision} /> : null}
                                                    {previewAssets.length ? <GeneratedImageViewer assets={previewAssets} /> : null}
                                                    {imageStatus === "not_generated" ? <p className="mt-3 text-sm text-slate-500">Image generation was requested, but no generated image asset was returned for this message.</p> : null}
                                                </div>
                                            );
                                        })}
                                        {pipelineUi.prompt &&
                                        pipelineUi.status !== "idle" &&
                                        pipelineUi.status !== "cancelled" &&
                                        !orderedMessages.some(
                                            (m) =>
                                                m.role === "user" &&
                                                String(m.message_text || "").trim() === pipelineUi.prompt?.trim(),
                                        ) ? (
                                            <div className={`ml-auto w-fit max-w-[70%] ${isStudioOpen ? "px-3" : "pr-10 pl-3"}`}>
                                                <div className="bg-[#F4F4F4] p-3 text-base text-[#353030]">
                                                    <p className="whitespace-pre-wrap">{pipelineUi.prompt}</p>
                                                </div>
                                            </div>
                                        ) : null}
                                        <ChatPipelinePanel
                                            state={pipelineUi}
                                            isApproving={isApproving}
                                            onApprove={(edited) => void handleApproveBlueprint(edited)}
                                            onCancel={() => void handleCancelBlueprint()}
                                            onImagesChange={(urls, fields, imageIndex) => {
                                                setPipelineUi((current) => {
                                                    const nextBlueprint = current.blueprint
                                                        ? { ...current.blueprint }
                                                        : null;
                                                    if (nextBlueprint && fields) {
                                                        if (
                                                            current.format === "carousel" &&
                                                            nextBlueprint.slides?.length &&
                                                            typeof imageIndex === "number"
                                                        ) {
                                                            const slides = [...nextBlueprint.slides];
                                                            const slide = { ...slides[imageIndex] };
                                                            slide.headline = fields.headline;
                                                            slide.supporting_line = fields.supporting_line;
                                                            slide.body = fields.body;
                                                            slide.cta = fields.cta;
                                                            slides[imageIndex] = slide;
                                                            nextBlueprint.slides = slides;
                                                        } else {
                                                            nextBlueprint.headline = fields.headline;
                                                            nextBlueprint.supporting_line = fields.supporting_line;
                                                            nextBlueprint.body = fields.body;
                                                            nextBlueprint.cta = fields.cta;
                                                        }
                                                    }
                                                    return {
                                                        ...current,
                                                        imageUrls: urls,
                                                        blueprint: nextBlueprint,
                                                    };
                                                });
                                            }}
                                        />
                                        <div ref={messageBottomRef} />
                                    </div>

                                    <div className={`shrink-0 ${isStudioOpen ? "px-3" : "pr-10 pl-3"}`}>
                                        {isGeneratingMessage ? (
                                            <div className="mb-5 flex items-center gap-2 text-sm font-medium text-primary">
                                                <span className="flex h-3.5 w-3.5 items-center justify-center rounded-[2px] bg-primary text-[10px] font-bold text-white">V</span>
                                                <span>Applying brand intelligence...</span>
                                            </div>
                                        ) : null}
                                        {attachedAssets.length ? (
                                            <div className="mb-3 flex flex-wrap gap-2">
                                                {attachedAssets.map((asset) => (
                                                    <button
                                                        key={asset.id}
                                                        type="button"
                                                        onClick={() => toggleReferenceAsset(asset)}
                                                        className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs text-primary"
                                                    >
                                                        <Paperclip className="h-3 w-3" />
                                                        <span>{assetPreviewLabel(asset)}</span>
                                                        <X className="h-3 w-3" />
                                                    </button>
                                                ))}
                                            </div>
                                        ) : null}
                                        {!pipelineBusy ? (
                                        <div className="mb-3">
                                            <TemplateRecommendationRail
                                                recommendations={templateRecommendations}
                                                isLoading={isFetchingTemplateRecommendations}
                                                selectedTemplateId={selectedTemplateId}
                                                onSelect={handleTemplateSelection}
                                            />
                                        </div>
                                        ) : null}
                                        {selectedTemplateLabel && !pipelineBusy ? (
                                            <p className="mb-3 text-xs text-slate-500">
                                                Pinned template: <span className="font-medium text-slate-700">{selectedTemplateLabel}</span>. We&apos;ll follow this visual direction unless auto mode is safer.
                                            </p>
                                        ) : null}
                                        {attachmentError ? <p className="mb-2 text-sm text-red-500">{attachmentError}</p> : null}
                                        {pipelineBusy ? (
                                            <p className="mb-2 text-center text-xs text-[#6A6E8B]">
                                                Pipeline in progress — Approve or Cancel on the blueprint card. Composer unlocks when done.
                                            </p>
                                        ) : (
                                        <SurfaceCard className={`flex items-end gap-3 border border-[#E1E4ED] bg-white px-3 pb-2 shadow-[0_14px_28px_-24px_rgba(15,23,42,0.45)]`}>
                                            <button
                                                type="button"
                                                onClick={() => attachmentInputRef.current?.click()}
                                                disabled={!canGenerateInWorkspace || isGeneratingMessage}
                                                className="flex h-8 w-8 shrink-0 items-center justify-center border border-[#D9DDE8] bg-[#F4F4F5] text-[#A1A1AA] disabled:cursor-not-allowed"
                                            >
                                                <Plus className="h-4 w-4" />
                                            </button>
                                            <Textarea
                                                ref={composerTextareaRef}
                                                value={composerDraft}
                                                onChange={(event) => setComposerDraft(event.target.value)}
                                                onKeyDown={handleComposerKeyDown}
                                                placeholder="What do you want to create today?"
                                                className="min-h-9 max-h-55 flex-1 resize-none overflow-y-hidden border-none bg-transparent px-0 pt-3.5 text-base leading-6 text-[#6A6E8B] shadow-none outline-none focus-visible:ring-0"
                                            />
                                            <button
                                                type="button"
                                                onClick={sendMessage.isPending ? cancelActiveGeneration : () => void dispatchGeneration(composerDraft)}
                                                disabled={!canGenerateInWorkspace || createSession.isPending || (!sendMessage.isPending && !composerDraft.trim())}
                                                aria-label={sendMessage.isPending ? "Stop generation" : "Send message"}
                                                className="flex h-8 min-w-8 shrink-0 items-center justify-center bg-[#F4F4F5] px-2 text-primary disabled:cursor-not-allowed disabled:text-slate-300"
                                            >
                                                {sendMessage.isPending ? (
                                                    <Square className="h-4 w-4" />
                                                ) : createSession.isPending ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <ArrowUp className="h-4 w-4" />
                                                )}
                                            </button>
                                        </SurfaceCard>
                                        )}
                                    </div>
                                    <p className="pt-4 text-center text-sm text-[#A0A0A7]">Violyt suggestions may need review. Verify accuracy before use.</p>
                                </div>
                                {isStudioOpen ? (
                                    <>
                                        <StudioPanel
                                            platform={studioPlatform}
                                            setPlatform={setStudioPlatform}
                                            format={studioFormat}
                                            setFormat={setStudioFormat}
                                            fileType={studioFileType}
                                            setFileType={setStudioFileType}
                                            sizeLabel={studioSizeLabel}
                                            setSizeLabel={setStudioSizeLabel}
                                            campaignGoal={campaignGoal}
                                            setCampaignGoal={setCampaignGoal}
                                            onToggle={() => setIsStudioOpen(false)}
                                            className="hidden xl:block"
                                        />
                                        {/* Mobile / tablet studio drawer */}
                                        <div className="xl:hidden fixed inset-0 z-40 flex justify-end bg-black/30" onClick={() => setIsStudioOpen(false)}>
                                            <div
                                                className="h-full w-[min(100%,320px)] bg-white shadow-xl"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                <StudioPanel
                                                    platform={studioPlatform}
                                                    setPlatform={setStudioPlatform}
                                                    format={studioFormat}
                                                    setFormat={setStudioFormat}
                                                    fileType={studioFileType}
                                                    setFileType={setStudioFileType}
                                                    sizeLabel={studioSizeLabel}
                                                    setSizeLabel={setStudioSizeLabel}
                                                    campaignGoal={campaignGoal}
                                                    setCampaignGoal={setCampaignGoal}
                                                    onToggle={() => setIsStudioOpen(false)}
                                                    className="min-h-full border-l-0"
                                                />
                                            </div>
                                        </div>
                                    </>
                                ) : null}
                            </div>
                        </div>
                    ) : (
                        <div className={`grid min-h-[calc(100vh-100px-68px)] ${isStudioOpen ? "xl:grid-cols-[minmax(0,1fr)_296px]" : "xl:grid-cols-1"}`}>
                            <div className="min-h-0 w-full overflow-y-auto">
                            {/* Header */}
                            <div className="flex h-[61px] py-10 items-center justify-between border-b border-[#E5E5EA] bg-white">
                                <div className="w-full flex items-center justify-between gap-3 px-4">
                                    <div className="flex gap-2 relative">
                                        <h1 className="font-dmSans text-3xl font-bold text-primary">{brand.name}</h1>
                                        <Link
                                            href={`/brand_space/${brandId}/edit`}
                                            className="absolute -right-7 -top-1 text-sm text-[#121212] hover:underline"
                                        >
                                            <Image src="/actions_icons/chat/redirect_link.svg" alt="Edit icon" width={19} height={19} className="inline-block mr-1" />
                                        </Link>
                                    </div>
                                    <UsageRing
                                        value={usageRemainingPercent}
                                        label={usagePendingLabel}
                                    />
                                </div>

                                <div className="flex items-center gap-4 px-4">
                                    <Button
                                        type="button"
                                        variant={"ghost"}
                                        onClick={() => setIsStudioOpen((current) => !current)}
                                        className={`flex h-10 w-10 items-center justify-center text-[#121212] ${isStudioOpen && "hidden"}`}
                                        aria-label={isStudioOpen ? "Hide Studio" : "Show Studio"}
                                    >
                                        {!isStudioOpen && <Image src="/actions_icons/toggle.svg" alt="Open studio" width={16} height={16} className="h-4 w-4" />}
                                    </Button>
                                </div>
                            </div>
                            {!canGenerateInWorkspace ? (
                                <div className="mx-auto max-w-4xl rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                                    This Brand Space is currently <span className="font-medium capitalize">{brandLifecycle}</span>. Finish activation before generating content or images in the workspace.
                                </div>
                            ) : null}
                            <div className="mx-auto flex w-full max-w-3xl flex-col items-center px-4 pt-[8vh]">
                                <div className="flex items-center gap-5">
                                    <Image src="/logo.svg" alt="Violyt Icon" width={40} height={40} className="" />
                                    <h2 className="font-dmSans text-2xl md:text-3xl xl:text-4xl font-medium tracking-normal text-[#121212]">Greeting message</h2>
                                </div>

                                <SurfaceCard className="mt-9 w-full border border-[#DDE1EA] bg-white px-4 py-3 shadow-[0_16px_30px_-25px_rgba(15,23,42,0.45)]">
                                    <Textarea
                                        ref={promptTextareaRef}
                                        placeholder="What do you want to create today?"
                                        className="min-h-20 max-h-55 resize-none overflow-y-hidden border-none bg-transparent p-0 text-sm leading-6 text-[#74789A] shadow-none focus-visible:ring-0"
                                        value={workspacePrompt}
                                        onChange={(event) => setWorkspacePrompt(event.target.value)}
                                        onKeyDown={handlePromptKeyDown}
                                    />
                                    <p className="mt-3 text-xs text-[#8A8A8A]">
                                        Set Format / Platform / Size in the Studio panel on the right.
                                    </p>
                                    <div className="mt-3 flex items-center justify-between">
                                        <button
                                            type="button"
                                            onClick={() => attachmentInputRef.current?.click()}
                                            disabled={!canGenerateInWorkspace || isGeneratingMessage}
                                            className="flex h-8 w-8 items-center justify-center border border-[#D9DDE8] bg-[#F4F4F5] text-[#A1A1AA] disabled:cursor-not-allowed"
                                        >
                                            <Plus className="h-4 w-4" />
                                        </button>
                                        <button
                                            type="button"
                                            onClick={sendMessage.isPending ? cancelActiveGeneration : () => void dispatchGeneration(workspacePrompt)}
                                            disabled={!canGenerateInWorkspace || createSession.isPending || (!sendMessage.isPending && !workspacePrompt.trim())}
                                            aria-label={sendMessage.isPending ? "Stop generation" : "Send message"}
                                            className="flex h-8 min-w-8 items-center justify-center bg-primary px-2 text-white disabled:cursor-not-allowed disabled:bg-slate-200"
                                        >
                                            {sendMessage.isPending ? (
                                                <Square className="h-4 w-4" />
                                            ) : createSession.isPending ? (
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                            ) : (
                                                <ArrowUp className="h-4 w-4" />
                                            )}
                                        </button>
                                    </div>
                                </SurfaceCard>
                                {attachedAssets.length ? (
                                    <div className="flex w-full flex-wrap justify-center gap-2">
                                        {attachedAssets.map((asset) => (
                                            <button
                                                key={asset.id}
                                                type="button"
                                                onClick={() => toggleReferenceAsset(asset)}
                                                className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-xs text-primary"
                                            >
                                                <Paperclip className="h-3 w-3" />
                                                <span>{assetPreviewLabel(asset)}</span>
                                                <X className="h-3 w-3" />
                                            </button>
                                        ))}
                                    </div>
                                ) : null}
                                <div className="w-full">
                                    <TemplateRecommendationRail
                                        recommendations={templateRecommendations}
                                        isLoading={isFetchingTemplateRecommendations}
                                        selectedTemplateId={selectedTemplateId}
                                        onSelect={handleTemplateSelection}
                                    />
                                </div>
                                {selectedTemplateLabel ? (
                                    <p className="text-sm text-slate-500">
                                        Pinned template: <span className="font-medium text-slate-700">{selectedTemplateLabel}</span>. Clear it any time to go back to auto selection.
                                    </p>
                                ) : null}

                                <div className="mt-6 flex flex-wrap justify-center gap-3">
                                    {actionOptions.map((action) => (
                                        <ActionButton
                                            key={action.id}
                                            selected={selectedAction === action.id}
                                            onClick={() => {
                                                setSelectedAction((current) => (current === action.id ? "none" : action.id));
                                                setActionPlatform("");
                                            }}
                                            icon={action.icon}
                                            label={action.label}
                                        />
                                    ))}
                                </div>
                                {/* <Link href={buildBrandSharingHref(brand)} className="inline-flex h-10 items-center gap-2 border border-[#D9DDE8] bg-white my-4 p-3 text-sm font-medium text-[#121212] hover:bg-slate-50">
                                    <BadgePlus className="h-4 w-4" />
                                    <span>Open Review</span>
                                </Link> */}

                                {activeActionOption ? (
                                    <SurfaceCard className="mt-6 w-full border border-[#DDE1EA] bg-white px-8 py-4 shadow-none">
                                        <div className="mb-6 flex items-center gap-2 text-[12px] font-medium text-[#121212]">
                                            <Image
                                                src={activeActionOption.icon}
                                                alt=""
                                                width={16}
                                                height={16}
                                                className="h-4 w-4"
                                            />
                                            <span>
                                                {selectedAction === "idea" && "Generate Campaign Idea"}
                                                {selectedAction === "social" && "Create Social Media Post"}
                                                {selectedAction === "repurpose" && "Repurpose Content"}
                                                {selectedAction === "alignment" && "Check Brand Alignment"}
                                            </span>
                                        </div>

                                        <div className="grid gap-5 md:max-w-md">
                                            {selectedAction === "idea" ? (
                                                <>
                                                    <FormField label="Campaign focus">
                                                        <StyledInput
                                                            placeholder="What product, service, or initiative is this campaign for"
                                                            value={campaignFocus}
                                                            onChange={(e) => setCampaignFocus(e.target.value)}
                                                        />
                                                    </FormField>
                                                    {/* <Label className="space-y-2"> */}
                                                    {/* <span className="text-sm font-normal text-[#121212]">Target Audience</span> */}
                                                    <FormField label="Target Audience">
                                                        <StyledSelect
                                                            value={campaignAudience}
                                                            onValueChange={(value) => setCampaignAudience(value)}
                                                            placeholder="Select target audience"
                                                            options={targetAudienceOptions}
                                                        />
                                                    </FormField>
                                                    {/* </Label> */}

                                                    <FormField label="Campaign Objective">
                                                        <StyledSelect
                                                            value={campaignObjective}
                                                            onValueChange={(value) => setCampaignObjective(value)}
                                                            placeholder="Select campaign objective"
                                                            options={campaignObjectiveOptions}
                                                        />
                                                    </FormField>
                                                </>
                                            ) : null}

                                            {selectedAction === "social" ? (
                                                <>
                                                    <FormField label="Topic">
                                                        <StyledInput
                                                            placeholder="What should this post be about"
                                                            value={socialTopic}
                                                            onChange={(e) => setSocialTopic(e.target.value)}
                                                        />
                                                    </FormField>
                                                    <FormField label="Goal">
                                                        <StyledInput
                                                            placeholder="What is the goal of this post"
                                                            value={socialGoal}
                                                            onChange={(e) => setSocialGoal(e.target.value)}
                                                        />
                                                    </FormField>
                                                </>
                                            ) : null}

                                            {selectedAction === "repurpose" ? (
                                                <>
                                                    <FormField label="Source Content">
                                                        <StyledInput
                                                            placeholder="Paste the content you would like to repurpose"
                                                            value={repurposeSource}
                                                            onChange={(e) => setRepurposeSource(e.target.value)}
                                                        />
                                                    </FormField>
                                                    <FormField label="Target">
                                                        <StyledInput
                                                            placeholder="Specify what the repurposed content should aim to achieve"
                                                            value={repurposeTarget}
                                                            onChange={(e) => setRepurposeTarget(e.target.value)}
                                                        />
                                                    </FormField>
                                                </>
                                            ) : null}

                                            {selectedAction === "alignment" ? (
                                                <label className="space-y-2">
                                                    <span className="text-sm font-normal text-[#121212]">Content</span>
                                                    <Textarea placeholder="Paste the content you want to evaluate for brand alignment" className="min-h-24 rounded-[8px] border-none bg-[#F3F5F8] text-xs shadow-none" value={alignmentContent} onChange={(event) => setAlignmentContent(event.target.value)} />
                                                </label>
                                            ) : null}

                                            {selectedAction !== "alignment" ? (
                                                <FormField label="Platform">
                                                    <StyledSelect
                                                        value={actionPlatform}
                                                        onValueChange={(value: string) => {
                                                            const platformValue = value as Platform | "";
                                                            setActionPlatform(platformValue);
                                                            if (platformValue) {
                                                                setStudioPlatform(platformValue);
                                                                setStudioSizeLabel(
                                                                    resolveSizeOptions(studioFormat, platformValue)[0].label
                                                                );
                                                            }
                                                        }}
                                                        placeholder="Select platform"
                                                        options={chatPlatformOptions}
                                                        getOptionLabel={(value) => platformLabels[value as Platform] || value}
                                                    />
                                                </FormField>
                                            ) : null}

                                            {/* <label className="space-y-2">
                                            <span className="text-sm font-normal text-[#121212]">Platform</span>
                                            <select
                                                className="h-9 w-full rounded-[8px] border-none bg-[#F3F5F8] px-3 text-xs text-[#8B8B94] outline-none"
                                                value={studioPlatform}
                                                onChange={(event) => {
                                                    const value = event.target.value as Platform;
                                                    setStudioPlatform(value);
                                                    setStudioSizeLabel(sizeOptionsByPlatform[value][0].label);
                                                }}
                                            >
                                                {platformOptions.map((option) => (
                                                    <option key={option} value={option}>
                                                        {option}
                                                    </option>
                                                ))}
                                            </select>
                                        </label> */}
                                        </div>

                                        <div className="mt-8 flex justify-end">
                                            <Button
                                                className="h-9 rounded-none bg-primary/72 p-6 text-base font-bold hover:bg-primary/90"
                                                onClick={handleActionGenerate}
                                                disabled={!canGenerateInWorkspace || isGeneratingMessage}
                                            >
                                                {selectedAction === "alignment" ? (toneCheck.isPending ? "Checking..." : "Generate") : isGeneratingMessage ? "Generating..." : "Generate"}
                                            </Button>
                                        </div>

                                        {toneCheck.data && selectedAction === "alignment" ? (
                                            <div className="mt-5 rounded-xl bg-slate-50 p-4 text-sm text-slate-700">
                                                <p className="font-semibold">Tone Score: {toneCheck.data.score}</p>
                                                <p className="mt-2">Deviations: {toneCheck.data.deviations.join(", ") || "None"}</p>
                                            </div>
                                        ) : null}
                                    </SurfaceCard>
                                ) : null}

                                {freshChatHistory.length ? (
                                    <div className="mt-9 w-full max-w-xl">
                                        <div className="mb-4 flex justify-center">
                                            <span className="bg-[#F4F4F4] px-4 py-2 text-base font-bold text-[#121212]">
                                                Chats
                                            </span>
                                        </div>
                                        <div className="space-y-5">
                                            {freshChatHistory.map((session) => {
                                                const title = session.title?.trim() || "Untitled chat";
                                                const updatedDate = formatChatHistoryDate(session.updated_at || session.created_at);
                                                return (
                                                    <Link
                                                        key={session.id}
                                                        href={buildBrandChatHref(brand, session.id)}
                                                        className="grid grid-cols-[minmax(0,1fr)_auto] gap-6 p-2 text-left transition hover:bg-[#F8F8F8]"
                                                    >
                                                        <span className="min-w-0">
                                                            <span className="block truncate text-base font-bold text-[#121212]">
                                                                {title}
                                                            </span>
                                                            <span className="mt-1 block truncate text-[15px] text-[#8A8A8A]">
                                                                Open previous chat
                                                            </span>
                                                        </span>
                                                        {updatedDate ? (
                                                            <span className="pt-0.5 text-sm text-[#9C9CA3]">{updatedDate}</span>
                                                        ) : null}
                                                    </Link>
                                                );
                                            })}
                                        </div>
                                    </div>
                                ) : null}

                            </div>
                            </div>
                            {isStudioOpen ? (
                                <>
                                    <StudioPanel
                                        platform={studioPlatform}
                                        setPlatform={setStudioPlatform}
                                        format={studioFormat}
                                        setFormat={setStudioFormat}
                                        fileType={studioFileType}
                                        setFileType={setStudioFileType}
                                        sizeLabel={studioSizeLabel}
                                        setSizeLabel={setStudioSizeLabel}
                                        campaignGoal={campaignGoal}
                                        setCampaignGoal={setCampaignGoal}
                                        onToggle={() => setIsStudioOpen(false)}
                                        className="hidden xl:block"
                                    />
                                    <div className="xl:hidden fixed inset-0 z-40 flex justify-end bg-black/30" onClick={() => setIsStudioOpen(false)}>
                                        <div
                                            className="h-full w-[min(100%,320px)] bg-white shadow-xl"
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            <StudioPanel
                                                platform={studioPlatform}
                                                setPlatform={setStudioPlatform}
                                                format={studioFormat}
                                                setFormat={setStudioFormat}
                                                fileType={studioFileType}
                                                setFileType={setStudioFileType}
                                                sizeLabel={studioSizeLabel}
                                                setSizeLabel={setStudioSizeLabel}
                                                campaignGoal={campaignGoal}
                                                setCampaignGoal={setCampaignGoal}
                                                onToggle={() => setIsStudioOpen(false)}
                                                className="min-h-full border-l-0"
                                            />
                                        </div>
                                    </div>
                                </>
                            ) : null}
                        </div>
                    )}
                </div>
                {/* <p className="bottom-0 mt-auto pb-3 pt-8 text-center text-sm text-[#A0A0A7]">Violyt suggestions may need review. Verify accuracy before use.</p> */}
            </div>
        </div>
    );
}
