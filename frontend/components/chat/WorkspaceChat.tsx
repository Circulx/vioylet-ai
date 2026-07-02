"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { type KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import {
    ArrowUp,
    Download,
    Loader2,
    Paperclip,
    Plus,
    Search,
    Share2,
    Square,
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
    GenerationDecision,
    KnowledgeAssetResponse,
    StudioPanelSelection,
    TemplateRecommendationResponse,
} from "@/lib/api/contracts";
import { buildBrandChatHref, buildBrandSharingHref, resolveBrandByRouteKey } from "@/lib/brand-routing";
import { useBrandUsage, useBrands } from "@/hooks/useBrands";
import {
    useChatMessages,
    useChatSessions,
    useCancelChatGeneration,
    useCreateChatSession,
    useExportContent,
    useSendChatMessage,
    useTemplateRecommendations,
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
import { FormField } from "../brandSpaces/tabs/FormFields";
import Image from "next/image";
import { AUDIENCE_OPTIONS } from "@/lib/brand-space-options";

type WorkspaceChatProps = { brandKey: string };
type Platform = "instagram" | "linkedin" | "x" | "youtube_thumbnail";
type FormatMode = "static" | "carousel" | "infographic" | "video";
type FileType = "doc" | "pdf" | "jpg" | "png";

const platformOptions: Platform[] = ["instagram", "linkedin"];
const platformLabels: Record<Platform, string> = {
    instagram: "Instagram",
    linkedin: "LinkedIn",
    x: "X",
    youtube_thumbnail: "YouTube",
};
const fileTypeOptions: FileType[] = ["doc", "pdf", "jpg", "png"];
const campaignGoalOptions = [
    "Brand Awareness",
    "Authority Building",
    "Trust & Credibility",
    "Consideration Influence",
    "Engagement Activation",
    "Community Growth",
];
const sizeOptionsByPlatform: Record<Platform, Array<{ label: string; width: number; height: number }>> = {
    instagram: [{ label: "1:1", width: 1080, height: 1080 }, { label: "9:16", width: 1080, height: 1920 }, { label: "4:5", width: 1080, height: 1350 }, { label: "16:9", width: 1200, height: 675 }],
    linkedin: [{ label: "1:1", width: 1080, height: 1080 }, { label: "9:16", width: 1080, height: 1920 }, { label: "4:5", width: 1080, height: 1350 }, { label: "16:9", width: 1200, height: 675 }],
    x: [{ label: "1:1", width: 1080, height: 1080 }, { label: "16:9", width: 1600, height: 900 }],
    youtube_thumbnail: [{ label: "16:9", width: 1280, height: 720 }],
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
    const highlightedParts = parts.map((part, index) => ({
        part,
        index,
        occurrenceIndex: parts
            .slice(0, index + 1)
            .filter((candidate) => candidate.toLowerCase() === trimmedQuery.toLowerCase()).length - 1,
        isMatch: part.toLowerCase() === trimmedQuery.toLowerCase(),
    }));
    return (
        <>
            {highlightedParts.map(({ part, index, occurrenceIndex, isMatch }) => {
                if (!isMatch) {
                    return <span key={`${part}-${index}`}>{part}</span>;
                }
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

function resolveGeneratedExportAssets(payload: ChatAssistantStructuredPayload | Record<string, unknown> | undefined) {
    if (!payload || Array.isArray(payload)) {
        return [];
    }
    const typedPayload = payload as ChatAssistantStructuredPayload;
    return (typedPayload.export_assets || []).filter((asset) => Boolean(asset.asset_url));
}

function resolvePreviousUserPrompt(messages: ChatMessageResponse[], currentIndex: number) {
    for (let index = currentIndex - 1; index >= 0; index -= 1) {
        const message = messages[index];
        if (message?.role === "user") {
            return message.message_text;
        }
    }
    return "";
}

const FILENAME_NOISE_WORDS = new Set([
    "a",
    "an",
    "the",
    "please",
    "create",
    "generate",
    "make",
    "design",
    "draft",
    "write",
    "build",
    "produce",
    "linkedin",
    "instagram",
    "facebook",
    "twitter",
    "youtube",
    "carousel",
    "post",
    "static",
    "image",
    "content",
    "creative",
    "infographic",
    "story",
    "reel",
    "png",
    "jpg",
    "jpeg",
    "pdf",
    "doc",
    "docx",
]);

function filenameTopicFromPrompt(prompt: string) {
    const withoutAudience = prompt
        .replace(/^target audience:\s*.*?(?:\n\n|\n|$)/i, " ")
        .replace(/\s+/g, " ")
        .trim();
    const firstSentence = withoutAudience.split(/[.!?]/)[0] || withoutAudience;
    const topicMatch = firstSentence.match(/\b(?:on|about|regarding|around|titled|called)\s+(.+)$/i);
    const topic = (topicMatch?.[1] || firstSentence)
        .replace(/^(?:please\s+)?(?:create|generate|make|design|draft|write|build|produce)\s+(?:me\s+)?(?:a|an|the)?\s*/i, "")
        .replace(/\b(?:focus|include|highlight|cover|explain|show)\b.*$/i, "")
        .trim();
    const tokens = topic
        .toLowerCase()
        .replace(/&/g, " and ")
        .replace(/[^a-z0-9\s-]/g, " ")
        .split(/[\s-]+/)
        .map((token) => token.trim())
        .filter((token) => token && !FILENAME_NOISE_WORDS.has(token));
    return tokens.slice(0, 12).join("-") || "generated-content";
}

function assetExtension(asset: AssetReference | undefined) {
    const mimeType = (asset?.mime_type || "").toLowerCase();
    if (mimeType.includes("pdf")) {
        return "pdf";
    }
    if (mimeType.includes("wordprocessingml") || mimeType.includes("msword")) {
        return "docx";
    }
    if (mimeType.includes("jpeg") || mimeType.includes("jpg")) {
        return "jpg";
    }
    if (mimeType.includes("png")) {
        return "png";
    }
    const storageExtension = (asset?.storage_path || "").split(".").pop()?.toLowerCase();
    return storageExtension && /^[a-z0-9]+$/.test(storageExtension) ? storageExtension : "png";
}

function generatedDownloadFilename(prompt: string, asset: AssetReference | undefined) {
    return `${filenameTopicFromPrompt(prompt)}.${assetExtension(asset)}`;
}

function generatedSlideDownloadFilename(prompt: string, asset: AssetReference | undefined, slideIndex: number, totalSlides: number) {
    const baseName = filenameTopicFromPrompt(prompt);
    const extension = assetExtension(asset);
    return totalSlides > 1 ? `${baseName}-slide-${slideIndex}.${extension}` : `${baseName}.${extension}`;
}

function assetMatchesFileType(asset: AssetReference, fileType: FileType) {
    const mimeType = (asset.mime_type || "").toLowerCase();
    if (fileType === "png") {
        return mimeType.includes("png");
    }
    if (fileType === "jpg") {
        return mimeType.includes("jpeg") || mimeType.includes("jpg");
    }
    if (fileType === "pdf") {
        return mimeType.includes("pdf");
    }
    return mimeType.includes("wordprocessingml") || mimeType.includes("msword");
}

function triggerDownload(url: string, filename: string) {
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.rel = "noopener noreferrer";
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    link.remove();
}

function downloadUrlWithFilename(url: string, filename: string) {
    try {
        const downloadUrl = new URL(url, window.location.href);
        downloadUrl.searchParams.set("filename", filename);
        downloadUrl.searchParams.set("download", "true");
        return downloadUrl.toString();
    } catch {
        return url;
    }
}

function downloadAsset(asset: AssetReference, filename: string) {
    const downloadUrl = asset.asset_url || "";
    if (!downloadUrl) {
        return;
    }
    triggerDownload(downloadUrlWithFilename(downloadUrl, filename), filename);
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

function GeneratedImageViewer({
    assets,
    existingExportAssets,
    contentVersionId,
    fileType,
    onExport,
    sourcePrompt,
}: {
    assets: AssetReference[];
    existingExportAssets: AssetReference[];
    contentVersionId: string;
    fileType: FileType;
    onExport: (contentVersionId: string) => Promise<AssetReference[]>;
    sourcePrompt: string;
}) {
    const [activeIndex, setActiveIndex] = useState(0);
    const [isSaving, setIsSaving] = useState(false);
    const imageAssets = assets
        .map((asset) => ({ ...asset, resolvedUrl: asset.asset_url || "" }))
        .filter((asset) => Boolean(asset.resolvedUrl));
    const activeAsset = imageAssets[Math.min(activeIndex, Math.max(imageAssets.length - 1, 0))];

    if (!activeAsset) {
        return null;
    }

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const matchingExistingAssets = existingExportAssets.filter((asset) => assetMatchesFileType(asset, fileType));
            const exportedAssets = matchingExistingAssets.length || !contentVersionId ? matchingExistingAssets : await onExport(contentVersionId);
            const downloadableAssets = exportedAssets.filter((asset) => Boolean(asset.asset_url));
            if (!downloadableAssets.length) {
                await downloadAsset(activeAsset, generatedDownloadFilename(sourcePrompt, activeAsset));
                return;
            }
            await Promise.all(
                downloadableAssets.map((asset, index) =>
                    downloadAsset(asset, generatedSlideDownloadFilename(sourcePrompt, asset, index + 1, downloadableAssets.length)),
                ),
            );
        } catch {
            await downloadAsset(activeAsset, generatedDownloadFilename(sourcePrompt, activeAsset));
        } finally {
            setIsSaving(false);
        }
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
                        onClick={() => void handleSave()}
                        disabled={isSaving}
                        className="inline-flex h-7 items-center gap-1.5 border border-primary bg-white px-2.5 text-[11px] font-medium text-primary"
                    >
                        {isSaving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                        <span>{isSaving ? "Preparing..." : "Save"}</span>
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
    dropdownId,
    value,
    onChange,
    options = campaignGoalOptions,
    placeholder = "Select",
    openDropdown,
    setOpenDropdown,
}: {
    dropdownId: "campaignGoal" | "targetAudience";
    value: string;
    onChange: (value: string) => void;
    options?: string[];
    placeholder?: string;
    openDropdown: "campaignGoal" | "targetAudience" | null;
    setOpenDropdown: (value: "campaignGoal" | "targetAudience" | null) => void;
}) {
    const dropdownRef = useRef<HTMLDivElement | null>(null);
    const menuRef = useRef<HTMLDivElement | null>(null);
    const isOpen = openDropdown === dropdownId;
    const selectedValues = useMemo(
        () => value.split(",").map((item) => item.trim()).filter(Boolean),
        [value],
    );

    useEffect(() => {
        if (!isOpen) {
            return;
        }

        const scrollFrame = window.requestAnimationFrame(() => {
            menuRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        });

        const handlePointerDown = (event: MouseEvent) => {
            if (!dropdownRef.current?.contains(event.target as Node)) {
                setOpenDropdown(null);
            }
        };
        const handleKeyDown = (event: globalThis.KeyboardEvent) => {
            if (event.key === "Escape") {
                setOpenDropdown(null);
            }
        };

        document.addEventListener("mousedown", handlePointerDown);
        document.addEventListener("keydown", handleKeyDown);
        return () => {
            window.cancelAnimationFrame(scrollFrame);
            document.removeEventListener("mousedown", handlePointerDown);
            document.removeEventListener("keydown", handleKeyDown);
        };
    }, [isOpen, setOpenDropdown]);

    const toggleOption = (option: string) => {
        const nextValues = selectedValues.includes(option)
            ? selectedValues.filter((item) => item !== option)
            : [...selectedValues, option];
        onChange(nextValues.join(", "));
    };

    return (
        <div ref={dropdownRef} className="relative">
            <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => setOpenDropdown(isOpen ? null : dropdownId)}
                className={`flex h-14 w-full items-center justify-between rounded-xl bg-section-input-field px-4 text-left text-sm transition-colors ${isOpen ? "rounded-b-none" : ""}`}
            >
                <span className={`truncate ${selectedValues.length ? "text-[#121212]" : "text-[#9A9AA2]"}`}>
                    {selectedValues.length ? selectedValues.join(", ") : placeholder}
                </span>
                <ChevronDown className={`h-5 w-5 shrink-0 text-[#8B8B94] transition-transform ${isOpen ? "rotate-180" : ""}`} />
            </button>
            {isOpen ? (
                <div ref={menuRef} className="max-h-86 overflow-y-auto rounded-b-xl border border-t-0 border-[#ECEEF5] bg-white shadow-[0_16px_30px_-22px_rgba(15,23,42,0.45)] thin-scrollbar">
                    {options.map((option) => (
                        <label
                            key={option}
                            className="flex min-h-14 cursor-pointer items-center gap-4 border-b border-[#F0F1F5] px-4 py-3 text-base text-[#121212] last:border-b-0 hover:bg-[#F8F8FA]"
                        >
                            <input
                                type="checkbox"
                                checked={selectedValues.includes(option)}
                                onChange={() => toggleOption(option)}
                                className="h-5 w-5 rounded border-[#8D8D95] accent-[#121212]"
                            />
                            <span className="min-w-0 flex-1 truncate">{option}</span>
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
    targetAudience,
    setTargetAudience,
    targetAudienceOptions,
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
    targetAudience: string;
    setTargetAudience: (value: string) => void;
    targetAudienceOptions: string[];
    onToggle?: () => void;
    className?: string;
}) {
    const sizeOptions = sizeOptionsByPlatform[platform];
    const [openStudioDropdown, setOpenStudioDropdown] = useState<"campaignGoal" | "targetAudience" | null>(null);

    return (
        <aside className={`w-full relative min-h-[calc(100vh-24px)] rounded-tl-xl rounded-bl-xl overflow-y-auto space-y-6 border-l border-[#E5E7F0] bg-[#F7F7FB] px-5 ${className || ""} thin-scrollbar`}>
            {/* Header */}
            <div className="sticky top-0 flex items-center justify-between py-5 bg-[#F7F7FB]">
                <h3 className="text-lg font-bold text-[#121212]">Studio</h3>
                <Button
                    type="button"
                    variant={"ghost"}
                    onClick={onToggle}
                    className={`flex h-10 w-10 items-center justify-center text-[#121212]`}
                >
                    <Image src="/toggleSidebar.svg" alt="Open panel" width={16} height={16} className="h-4 w-4" />
                    {/* <PanelRightClose className="h-4 w-4" /> */}
                </Button>
            </div>

            <div className="space-y-3">
                <p className="text-base font-medium text-[#121212]">Format</p>
                <div className="grid grid-cols-2 gap-2">
                    {[
                        { value: "static", label: "Static", enabled: true },
                        { value: "carousel", label: "Carousel", enabled: true },
                        { value: "infographic", label: "Infographic", enabled: true },
                        { value: "video", label: "Video", enabled: false },
                    ].map((option) => (
                        <Button
                            variant={"ghost"}
                            key={option.value}
                            type="button"
                            disabled={!option.enabled}
                            onClick={() => option.enabled && setFormat(option.value as FormatMode)}
                            className={`min-w-0 rounded-xl p-6 text-center text-sm font-medium ${format === option.value
                                ? "bg-[#EBEBEB] text-[#919191]"
                                : option.enabled
                                    ? "bg-white text-[#8D8D95]"
                                    : "cursor-not-allowed bg-white text-[#B8B8BE]"
                                }`}
                        >
                            {option.label}
                        </Button>
                    ))}
                </div>
            </div>

            <div className="space-y-3">
                <p className="text-base font-medium text-[#121212]">Size</p>
                <div className="flex gap-1 border-b border-[#D1D3DA]">
                    {platformOptions.map((option) => (
                        <Button
                            variant={"ghost"}
                            key={option}
                            onClick={() => {
                                setPlatform(option);
                                setSizeLabel(sizeOptionsByPlatform[option][0].label);
                            }}
                            className={`flex flex-1 rounded-none border-b-2 p-5 text-base font-normal ${platform === option ? "border-b-primary text-[#121212]" : "border-transparent text-[#393939]"
                                }`}
                        >
                            <span className="block truncate">{platformLabels[option]}</span>
                        </Button>
                    ))}
                </div>
                <div className="grid grid-cols-2 gap-2">
                    {sizeOptions.map((option) => (
                        <Button
                            variant={"ghost"}
                            key={option.label}
                            type="button"
                            onClick={() => setSizeLabel(option.label)}
                            className={`p-6 rounded-xl text-center text-sm font-medium text-[#919191] ${sizeLabel === option.label ? "bg-[#EBEBEB]" : "bg-white"
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
                            className={`p-6 text-[#919191] rounded-xl text-center text-sm font-medium uppercase ${fileType === option ? "bg-[#EBEBEB]" : "bg-white"
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
                        dropdownId="campaignGoal"
                        value={campaignGoal}
                        onChange={setCampaignGoal}
                        openDropdown={openStudioDropdown}
                        setOpenDropdown={setOpenStudioDropdown}
                    />
                </FormField>
            </div>

            <div className="space-y-3 pb-6">
                <FormField label="Target Audience">
                    <CampaignGoalMultiSelect
                        dropdownId="targetAudience"
                        value={targetAudience}
                        onChange={setTargetAudience}
                        options={targetAudienceOptions}
                        placeholder="Select target audience"
                        openDropdown={openStudioDropdown}
                        setOpenDropdown={setOpenStudioDropdown}
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
    const exportContent = useExportContent(brandId);
    const cancelChatGeneration = useCancelChatGeneration(brandId);
    const [workspacePrompt, setWorkspacePrompt] = useState("");
    const [composerDraft, setComposerDraft] = useState("");
    const [studioPlatform, setStudioPlatform] = useState<Platform>("instagram");
    const [studioFormat, setStudioFormat] = useState<FormatMode>("static");
    const [studioFileType, setStudioFileType] = useState<FileType>("png");
    const [studioSizeLabel, setStudioSizeLabel] = useState("1:1");
    const [campaignGoal, setCampaignGoal] = useState("");
    const [studioTargetAudience, setStudioTargetAudience] = useState("");
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
    const exportAssetCacheRef = useRef(new Map<string, AssetReference[]>());
    const exportWarmupRef = useRef(new Set<string>());

    const sizeOption = useMemo(
        () => sizeOptionsByPlatform[studioPlatform].find((entry) => entry.label === studioSizeLabel) || sizeOptionsByPlatform[studioPlatform][0],
        [studioPlatform, studioSizeLabel],
    );
    const studioPanel = useMemo<StudioPanelSelection>(
        () => ({
            format: studioFormat === "video" ? "static" : studioFormat,
            platform_preset: studioPlatform,
            file_type: studioFileType,
            size: { width: sizeOption.width, height: sizeOption.height },
        }),
        [sizeOption.height, sizeOption.width, studioFileType, studioFormat, studioPlatform],
    );
    const exportGeneratedAssetsForType = useCallback(async (contentVersionId: string, fileType: FileType) => {
        if (!contentVersionId) {
            return [];
        }
        const cacheKey = `${contentVersionId}:${fileType}`;
        const cachedAssets = exportAssetCacheRef.current.get(cacheKey);
        if (cachedAssets?.length) {
            return cachedAssets;
        }
        const response = await exportContent.mutateAsync({
            content_version_id: contentVersionId,
            export_format: fileType,
            studio_panel: { file_type: fileType },
        });
        const assets = response.export_assets || [];
        if (assets.length) {
            exportAssetCacheRef.current.set(cacheKey, assets);
        }
        return assets;
    }, [exportContent]);
    const exportGeneratedAssets = useCallback(
        (contentVersionId: string) => exportGeneratedAssetsForType(contentVersionId, studioFileType),
        [exportGeneratedAssetsForType, studioFileType],
    );
    const brandLifecycle = brand?.lifecycle_state || "draft";
    const canGenerateInWorkspace = brandLifecycle === "active";
    const isGeneratingMessage = createSession.isPending || sendMessage.isPending;
    const recommendationPrompt = useMemo(
        () => [composerDraft.trim() || workspacePrompt.trim(), campaignGoal, studioTargetAudience]
            .map((item) => item.trim())
            .filter(Boolean)
            .join("\n"),
        [campaignGoal, composerDraft, studioTargetAudience, workspacePrompt],
    );
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
    const hasConversation = Boolean((messages || []).length);
    const allocationPercent = brandUsage?.capacity_percent ?? 0;
    const usedWithinAllocationPercent = brandUsage?.usage_percent ?? 0;
    const usageRemainingPercent = Math.max(
        0,
        Math.min(100, Math.round((allocationPercent * (100 - usedWithinAllocationPercent)) / 100)),
    );
    const usagePendingLabel = `Pending Usage: ${usageRemainingPercent}%`;
    // const freshChatHistory = useMemo(
    //     () =>
    //         [...(sessions || [])]
    //             .filter((session) => session.id !== resolvedActiveSessionId || session.title?.trim())
    //             .sort((left: ChatSessionResponse, right: ChatSessionResponse) =>
    //                 new Date(right.updated_at || right.created_at).getTime() - new Date(left.updated_at || left.created_at).getTime(),
    //             )
    //             .slice(0, 8),
    //     [resolvedActiveSessionId, sessions],
    // );
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
    useEffect(() => {
        const latestGeneratedMessage = [...orderedMessages]
            .reverse()
            .find((message) => message.role === "assistant" && resolveGeneratedImageAssets(message.structured_payload).length);
        if (!latestGeneratedMessage) {
            return;
        }
        const contentVersionId =
            latestGeneratedMessage.content_version_id ||
            (latestGeneratedMessage.structured_payload as ChatAssistantStructuredPayload)?.content_version_id ||
            "";
        if (!contentVersionId) {
            return;
        }

        for (const asset of resolveGeneratedExportAssets(latestGeneratedMessage.structured_payload)) {
            for (const fileType of fileTypeOptions) {
                if (assetMatchesFileType(asset, fileType)) {
                    const cacheKey = `${contentVersionId}:${fileType}`;
                    const currentAssets = exportAssetCacheRef.current.get(cacheKey) || [];
                    if (!currentAssets.some((current) => current.asset_url === asset.asset_url || current.storage_path === asset.storage_path)) {
                        exportAssetCacheRef.current.set(cacheKey, [...currentAssets, asset]);
                    }
                }
            }
        }

        let cancelled = false;
        void (async () => {
            for (const fileType of fileTypeOptions) {
                const cacheKey = `${contentVersionId}:${fileType}`;
                if (cancelled || exportAssetCacheRef.current.get(cacheKey)?.length || exportWarmupRef.current.has(cacheKey)) {
                    continue;
                }
                exportWarmupRef.current.add(cacheKey);
                try {
                    await exportGeneratedAssetsForType(contentVersionId, fileType);
                } catch {
                    exportWarmupRef.current.delete(cacheKey);
                }
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [exportGeneratedAssetsForType, orderedMessages]);
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
        if (isGeneratingMessage) {
            return;
        }
        if (!message.trim()) {
            setWorkspaceError("Enter a prompt before sending.");
            return;
        }
        try {
            setWorkspaceError("");
            setGenerationProgressIndex(0);
            const sessionId = await ensureSession();
            const selectedAudiences = studioTargetAudience.split(",").map((item) => item.trim()).filter(Boolean);
            const outgoingMessage = selectedAudiences.length
                ? `Target audience: ${selectedAudiences.join(", ")}\n\n${message}`
                : message;
            const controller = new AbortController();
            activeGenerationControllerRef.current = controller;
            activeGenerationSessionRef.current = sessionId;
            await sendMessage.mutateAsync({
                sessionId,
                data: {
                    message: outgoingMessage,
                    studio_panel: studioPanel,
                    generate_image: studioFormat !== "video",
                    template_id: selectedTemplateId || undefined,
                    reference_asset_ids: attachedAssets.map((asset) => asset.id),
                },
                signal: controller.signal,
            });
            setComposerDraft("");
            setWorkspacePrompt((current) => (current.trim() === message.trim() ? "" : current));
            setAttachedAssets([]);
            setAttachmentError("");
        } catch (error) {
            if (isRequestCanceled(error)) {
                return;
            }
            setWorkspaceError(extractApiError(error, "Unable to start the workspace session right now."));
        } finally {
            activeGenerationControllerRef.current = null;
            activeGenerationSessionRef.current = "";
        }
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
                    {hasConversation && (
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
                                                        className="h-10 w-68 rounded-md border-[#E1E3EC] bg-blue pl-10 pr-24 text-sm text-[#77759A] shadow-none focus-visible:ring-0"
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
                                            {!isStudioOpen ? (
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
                                        {orderedMessages.map((message, messageIndex) => {
                                            const previewAssets = message.role === "assistant" ? resolveGeneratedImageAssets(message.structured_payload) : [];
                                            const existingExportAssets = message.role === "assistant" ? resolveGeneratedExportAssets(message.structured_payload) : [];
                                            const sourcePrompt = message.role === "assistant" ? resolvePreviousUserPrompt(orderedMessages, messageIndex) : "";
                                            const contentVersionId =
                                                message.content_version_id ||
                                                (message.structured_payload as ChatAssistantStructuredPayload)?.content_version_id ||
                                                "";
                                            const previewUrl = previewAssets[0]?.asset_url || undefined;
                                            const generationDecision = message.role === "assistant" ? resolveGenerationDecision(message.structured_payload) : null;
                                            const imageStatus =
                                                message.role === "assistant" &&
                                                    !previewUrl &&
                                                    (message.structured_payload as ChatAssistantStructuredPayload)?.image_generation_requested
                                                    ? (message.structured_payload as ChatAssistantStructuredPayload).image_generation_status
                                                    : null;
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
                                                    <div className={`p-3 text-base text-[#353030] rounded-md  ${message.role === "user"
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
                                                    {previewAssets.length ? (
                                                        <GeneratedImageViewer
                                                            assets={previewAssets}
                                                            existingExportAssets={existingExportAssets}
                                                            contentVersionId={contentVersionId}
                                                            fileType={studioFileType}
                                                            onExport={exportGeneratedAssets}
                                                            sourcePrompt={sourcePrompt}
                                                        />
                                                    ) : null}
                                                    {imageStatus === "not_generated" ? <p className="mt-3 text-sm text-slate-500">Image generation was requested, but no generated image asset was returned for this message.</p> : null}
                                                </div>
                                            );
                                        })}
                                        {isGeneratingMessage ? (
                                            <div className="mr-auto max-w-[86%]">
                                                <div className="bg-[#F6F6F7] px-5 py-4 text-[#222222]">
                                                    <div className="space-y-4">
                                                        <GenerationPreviewPlaceholder
                                                            width={studioPanel.size?.width ?? 1080}
                                                            height={studioPanel.size?.height ?? 1080}
                                                        />
                                                        <div className="flex items-center gap-3">
                                                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                                            <p className="min-w-0 text-sm font-medium text-slate-700">
                                                                <span className="block truncate">{activeGenerationStatusLine}</span>
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        ) : null}
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
                                        <div className="mb-3">
                                            <TemplateRecommendationRail
                                                recommendations={templateRecommendations}
                                                isLoading={isFetchingTemplateRecommendations}
                                                selectedTemplateId={selectedTemplateId}
                                                onSelect={handleTemplateSelection}
                                            />
                                        </div>
                                        {selectedTemplateLabel ? (
                                            <p className="mb-3 text-xs text-slate-500">
                                                Pinned template: <span className="font-medium text-slate-700">{selectedTemplateLabel}</span>. We&apos;ll follow this visual direction unless auto mode is safer.
                                            </p>
                                        ) : null}
                                        {attachmentError ? <p className="mb-2 text-sm text-red-500">{attachmentError}</p> : null}
                                        <SurfaceCard className={`flex items-end gap-3 rounded-xl border border-[#E1E4ED] bg-white px-3 pb-2 shadow-[0_14px_28px_-24px_rgba(15,23,42,0.45)]`}>
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
                                    </div>
                                    <p className="pt-4 text-center text-sm text-[#A0A0A7]">Violyt suggestions may need review. Verify accuracy before use.</p>
                                </div>
                                {isStudioOpen ? (
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
                                        targetAudience={studioTargetAudience}
                                        setTargetAudience={setStudioTargetAudience}
                                        targetAudienceOptions={targetAudienceOptions}
                                        onToggle={() => setIsStudioOpen(false)}
                                        className="hidden xl:block"
                                    />
                                ) : null}
                            </div>
                        </div>
                    )}
                    {!hasConversation && (
                        <div className="flex h-[calc(100vh-32px)] flex-col">
                            <div className={`grid min-h-0 flex-1 ${isStudioOpen ? "xl:grid-cols-[minmax(0,1fr)_296px]" : "xl:grid-cols-1"}`}>
                                <div className="min-h-0 overflow-y-auto bg-white">
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

                                <div className="flex items-center gap-4">
                                    {hasConversation ? (
                                        <div className="relative hidden md:block">
                                            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#77759A]" />
                                            <Input
                                                placeholder="Search"
                                                className="h-9 w-[214px] rounded-none border-[#E1E3EC] bg-blue pl-10 text-sm text-[#77759A] shadow-none focus-visible:ring-0"
                                            />
                                        </div>
                                    ) : null}
                                    {!isStudioOpen ? (
                                        <Button
                                            type="button"
                                            variant={"ghost"}
                                            onClick={() => setIsStudioOpen((current) => !current)}
                                            className={`flex h-10 w-10 items-center justify-center text-[#121212] ${isStudioOpen && 'hidden'}`}
                                            aria-label={isStudioOpen ? "Hide Studio" : "Show Studio"}
                                        >
                                            {!isStudioOpen && <Image src="/toggleSidebar.svg" alt="Open panel" width={16} height={16} className="h-4 w-4" />}
                                        </Button>
                                    ) : null}
                                </div>
                            </div>
                            {!canGenerateInWorkspace ? (
                                <div className="mx-auto max-w-4xl rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                                    This Brand Space is currently <span className="font-medium capitalize">{brandLifecycle}</span>. Finish activation before generating content or images in the workspace.
                                </div>
                            ) : null}
                            <div className="max-w-5xl mx-auto flex flex-col items-center px-4 my-[22vh]">
                                <div className="flex items-center gap-5">
                                    <Image src="/logo.svg" alt="Violyt Icon" width={40} height={40} className="" />
                                    <h2 className="font-dmSans text-2xl md:text-3xl xl:text-4xl font-medium tracking-normal text-[#121212]">Greeting message</h2>
                                </div>

                                <SurfaceCard className="mt-9 w-full rounded-xl border border-[#DDE1EA] bg-white px-4 py-3 shadow-[0_16px_30px_-25px_rgba(15,23,42,0.45)]">
                                    <Textarea
                                        ref={promptTextareaRef}
                                        placeholder="What do you want to create today?"
                                        className="min-h-20 max-h-55 resize-none overflow-y-hidden border-none bg-transparent p-0 text-sm leading-6 text-[#74789A] shadow-none focus-visible:ring-0"
                                        value={workspacePrompt}
                                        onChange={(event) => setWorkspacePrompt(event.target.value)}
                                        onKeyDown={handlePromptKeyDown}
                                    />
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

                                </div>
                                </div>
                                {isStudioOpen ? (
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
                                        targetAudience={studioTargetAudience}
                                        setTargetAudience={setStudioTargetAudience}
                                        targetAudienceOptions={targetAudienceOptions}
                                        onToggle={() => setIsStudioOpen(false)}
                                        className="hidden xl:block"
                                    />
                                ) : null}
                            </div>
                        </div>
                    )}
                </div>
                {/* <p className="bottom-0 mt-auto pb-3 pt-8 text-center text-sm text-[#A0A0A7]">Violyt suggestions may need review. Verify accuracy before use.</p> */}
            </div>
        </div>
    );
}
