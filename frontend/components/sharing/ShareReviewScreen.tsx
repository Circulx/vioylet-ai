"use client";

import { Bell, Copy, Download, Facebook, FileText, Folder, Grid2X2, Home, Image as ImageIcon, Instagram, Linkedin, PanelLeftClose, SendHorizontal, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SurfaceCard } from "@/components/common/DesignPrimitives";
import { resolveBrandByRouteKey } from "@/lib/brand-routing";
import { apiOrigin } from "@/lib/env";
import { useBrands } from "@/hooks/useBrands";
import { useProfile } from "@/hooks/useAuthProfile";
import { useAddReviewComment, useContentHistory, useCreateShareLink, useReviewDetail, useUpdateReviewStatus } from "@/hooks/useContentWorkspace";
import type { AssetReference } from "@/lib/api/contracts";
import { getAccessToken } from "@/lib/api/session";
import { coerceGenerationDecision, formatGenerationMode, getGenerationDecisionReasons, getGenerationDecisionTemplate } from "@/lib/generation-decision";
import Image from "next/image";

type ShareReviewScreenProps = {
    brandKey?: string;
    reviewToken?: string;
    externalMode?: boolean;
};

type ModalMode = "none" | "share" | "save";

function resolveAssetUrl(storagePath?: string | null) {
    return storagePath ? `${apiOrigin}/storage/${storagePath}` : null;
}

function resolveAssetByExtension(storagePath: string | undefined, extension: string) {
    if (!storagePath) {
        return false;
    }
    return storagePath.toLowerCase().endsWith(extension);
}

function CommentBubbleIcon({ className = "" }: { className?: string }) {
    return (
        <span className={`flex items-center justify-center rounded-full bg-primary ${className}`}>
            <span className="space-y-[4px]">
                <span className="block h-[2px] w-[14px] rounded-full bg-white" />
                <span className="block h-[2px] w-[9px] rounded-full bg-white" />
            </span>
        </span>
    );
}

function dedupeAssets(assets: AssetReference[]) {
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

const COMMENT_AVATAR_COLORS = ["#52B2CF", "#EF5A55", "#3F3192", "#4F9D69", "#D88C3A", "#7A6BD6"];

function stableCommentColor(seed: string) {
    const normalizedSeed = seed.trim().toLowerCase() || "reviewer";
    let hash = 0;
    for (let index = 0; index < normalizedSeed.length; index += 1) {
        hash = (hash * 31 + normalizedSeed.charCodeAt(index)) % COMMENT_AVATAR_COLORS.length;
    }
    return COMMENT_AVATAR_COLORS[hash];
}

function assetSequenceIndex(asset: AssetReference, fallbackIndex: number) {
    const metadata = (asset as AssetReference & { metadata?: Record<string, unknown> }).metadata || {};
    const metadataIndex = Number(metadata.slide_index || metadata.page_index || metadata.order);
    if (Number.isFinite(metadataIndex) && metadataIndex > 0) {
        return metadataIndex;
    }
    const path = `${asset.storage_path || ""} ${asset.asset_url || ""}`;
    const match = path.match(/(?:slide|page|p)[-_]?(\d+)/i);
    if (match) {
        return Number(match[1]);
    }
    return fallbackIndex + 1;
}

function sortAssetsBySequence(assets: AssetReference[]) {
    return assets
        .map((asset, index) => ({ asset, sequence: assetSequenceIndex(asset, index), index }))
        .sort((left, right) => left.sequence - right.sequence || left.index - right.index)
        .map((entry) => entry.asset);
}

function hasSequenceHint(asset: AssetReference) {
    const metadata = (asset as AssetReference & { metadata?: Record<string, unknown> }).metadata || {};
    if (metadata.slide_index || metadata.page_index || metadata.order) {
        return true;
    }
    const path = `${asset.storage_path || ""} ${asset.asset_url || ""}`;
    return /(?:slide|page|p)[-_]?\d+/i.test(path);
}

function expectedSlideCount(payload: unknown) {
    if (!payload || Array.isArray(payload) || typeof payload !== "object") {
        return 0;
    }
    const metadata = (payload as Record<string, unknown>).metadata;
    if (!metadata || Array.isArray(metadata) || typeof metadata !== "object") {
        return 0;
    }
    const carouselSpecs = (metadata as Record<string, unknown>).carousel_slide_specs;
    return Array.isArray(carouselSpecs) ? carouselSpecs.length : 0;
}

function assetFamilyKey(asset: AssetReference) {
    const path = asset.storage_path || asset.asset_url || "";
    const filename = path.split(/[\\/]/).pop() || path;
    if (filename.startsWith("edited-")) {
        return "edited";
    }
    if (filename.startsWith("export-")) {
        return "export";
    }
    if (filename.startsWith("exact-footer-")) {
        return "exact-footer";
    }
    if (filename.startsWith("generated-")) {
        return "generated";
    }
    return asset.asset_role || "asset";
}

function chooseDisplayFamily(assets: AssetReference[], payload: unknown) {
    const sorted = sortAssetsBySequence(dedupeAssets(assets));
    if (sorted.length <= 1) {
        return sorted;
    }
    const groups = new Map<string, AssetReference[]>();
    for (const asset of sorted) {
        const key = assetFamilyKey(asset);
        groups.set(key, [...(groups.get(key) || []), asset]);
    }
    const expectedCount = expectedSlideCount(payload);
    const grouped = Array.from(groups.entries());
    if (expectedCount > 1) {
        const exactEdited = grouped.find(([key, value]) => key === "edited" && value.length === expectedCount);
        if (exactEdited) {
            return exactEdited[1];
        }
        const exactMatch = grouped.find(([, value]) => value.length === expectedCount);
        if (exactMatch) {
            return exactMatch[1];
        }
    }
    const edited = groups.get("edited");
    if (edited?.length) {
        return edited;
    }
    const exportGroup = groups.get("export");
    if (exportGroup?.length) {
        return expectedCount > 1 ? exportGroup.slice(0, expectedCount) : exportGroup.slice(0, 1);
    }
    return sorted.some(hasSequenceHint) ? sorted : sorted.slice(0, 1);
}

function getPayloadAssets(payload: unknown, key: "export_assets" | "assets") {
    if (!payload || Array.isArray(payload) || typeof payload !== "object") {
        return [];
    }
    const value = (payload as Record<string, unknown>)[key];
    return Array.isArray(value) ? value.filter((asset): asset is AssetReference => Boolean(asset && typeof asset === "object")) : [];
}

function getPayloadPreviewAsset(payload: unknown) {
    if (!payload || Array.isArray(payload) || typeof payload !== "object") {
        return null;
    }
    const asset = (payload as Record<string, unknown>).preview_asset;
    return asset && typeof asset === "object" ? asset as AssetReference : null;
}

function resolveReviewDisplayAssets(reviewContent: { generated_payload?: unknown; assets?: AssetReference[] } | undefined, fallbackAssets?: AssetReference[]) {
    const displayAssets = (reviewContent as { display_assets?: AssetReference[] } | undefined)?.display_assets?.filter(
        (asset) => asset.mime_type.startsWith("image/") && Boolean(asset.asset_url),
    ) || [];
    if (displayAssets.length) {
        return sortAssetsBySequence(dedupeAssets(displayAssets));
    }

    const payload = reviewContent?.generated_payload;
    const exportImages = getPayloadAssets(payload, "export_assets").filter(
        (asset) => asset.mime_type?.startsWith("image/") && Boolean(asset.asset_url),
    );
    if (exportImages.length) {
        return sortAssetsBySequence(dedupeAssets(exportImages));
    }

    const previewAsset = getPayloadPreviewAsset(payload);
    if (previewAsset?.asset_url && previewAsset.mime_type?.startsWith("image/")) {
        return [previewAsset];
    }

    const payloadImages = getPayloadAssets(payload, "assets").filter(
        (asset) =>
            asset.mime_type?.startsWith("image/") &&
            Boolean(asset.asset_url) &&
            ["render_export", "render_preview", "ai_image"].includes(asset.asset_role),
    );
    if (payloadImages.length) {
        return sortAssetsBySequence(dedupeAssets(payloadImages));
    }

    const dbAssets = reviewContent?.assets || fallbackAssets || [];
    const dbExportImages = dbAssets.filter(
        (asset) => asset.mime_type.startsWith("image/") && asset.asset_role === "render_export",
    );
    if (dbExportImages.length) {
        return chooseDisplayFamily(dbExportImages, payload);
    }
    const dbPreviewImages = dbAssets.filter(
        (asset) => asset.mime_type.startsWith("image/") && asset.asset_role === "render_preview",
    );
    if (dbPreviewImages.length) {
        return [sortAssetsBySequence(dedupeAssets(dbPreviewImages))[0]];
    }
    return dedupeAssets(dbAssets.filter((asset) => asset.mime_type.startsWith("image/"))).slice(0, 1);
}

function ReviewImageViewer({
    assets,
    activeIndex,
    onActiveIndexChange,
    onSave,
    onShare,
    onClose,
}: {
    assets: AssetReference[];
    activeIndex: number;
    onActiveIndexChange: (index: number) => void;
    onSave: () => void;
    onShare: () => void;
    onClose: () => void;
}) {
    const imageAssets = assets
        .map((asset) => ({ ...asset, resolvedUrl: asset.asset_url || resolveAssetUrl(asset.storage_path) || "" }))
        .filter((asset) => Boolean(asset.resolvedUrl));
    const activeAsset = imageAssets[Math.min(activeIndex, Math.max(imageAssets.length - 1, 0))];

    return (
        <div className="relative min-h-[calc(100vh-12rem)] px-4 py-5">
            <div className="absolute left-4 top-4">
                <button type="button" onClick={onClose} className="flex h-7 w-7 items-center justify-center bg-white text-[#4B4B4B]">
                    <X className="h-4 w-4" />
                </button>
            </div>
            <div className="absolute right-4 top-5 flex items-center gap-3">
                <Button
                    type="button"
                    variant="outline"
                    onClick={onSave}
                    className="h-8 rounded-none border-primary bg-white p-5 text-base font-medium text-primary hover:bg-primary/5"
                >
                    <Download className="mr-1.5 h-3.5 w-3.5" />
                    Save
                </Button>
                <Button
                    type="button"
                    onClick={onShare}
                    className="h-8 rounded-none bg-primary/72 p-5 text-base font-medium text-white hover:bg-primary/90"
                >
                    <Image src="/actions_icons/share.svg" alt="share icon" width={16} height={16} />
                    Share
                </Button>
            </div>

            <div className="mx-auto flex min-h-[calc(100vh-12rem)] max-w-[940px] items-center justify-center gap-9 pt-14">
                <div className="flex min-h-[305px] flex-1 items-center justify-center bg-[#F1F2F6] p-7">
                    {activeAsset ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={activeAsset.resolvedUrl} alt="Review preview" className="max-h-[520px] w-auto max-w-full object-contain" />
                    ) : (
                        <div className="text-sm text-slate-500">No preview available yet.</div>
                    )}
                </div>
                {imageAssets.length > 1 ? (
                    <div className="flex max-h-[390px] w-[120px] shrink-0 flex-col gap-5 overflow-y-auto pr-1">
                        {imageAssets.map((asset, index) => (
                            <button
                                key={asset.asset_id || asset.storage_path || asset.asset_url || index}
                                type="button"
                                onClick={() => onActiveIndexChange(index)}
                                className={`border bg-white p-1 transition ${index === activeIndex ? "border-primary" : "border-transparent hover:border-[#D9DDE8]"
                                    }`}
                            >
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img src={asset.resolvedUrl} alt={`Review preview ${index + 1}`} className="h-16 w-full object-cover" />
                            </button>
                        ))}
                    </div>
                ) : null}
            </div>
        </div>
    );
}

export default function ShareReviewScreen({
    brandKey,
    reviewToken: reviewTokenProp,
    externalMode = false,
}: ShareReviewScreenProps) {
    const initialToken = reviewTokenProp || "";
    const [reviewToken, setReviewToken] = useState(initialToken);
    const [comment, setComment] = useState("");
    const [replyDrafts, setReplyDrafts] = useState<Record<string, string>>({});
    const [reviewerName, setReviewerName] = useState("");
    const [welcomeName, setWelcomeName] = useState("");
    const [modalMode, setModalMode] = useState<ModalMode>("none");
    const [copied, setCopied] = useState(false);
    const [activePreviewIndex, setActivePreviewIndex] = useState(0);
    const [hasAuthToken] = useState(() => Boolean(getAccessToken()));

    const { data: brands } = useBrands(Boolean(brandKey) && !externalMode);
    const profile = useProfile(hasAuthToken);
    const liveBrand = useMemo(
        () => resolveBrandByRouteKey(brands, brandKey),
        [brands, brandKey],
    );
    const brand = liveBrand;
    const brandId = liveBrand?.id || "";

    const { data: history } = useContentHistory(brandId);
    const latestContent = history?.[0];
    const createLink = useCreateShareLink(brandId);
    const review = useReviewDetail(reviewToken);
    const addComment = useAddReviewComment(reviewToken);
    const updateReviewStatus = useUpdateReviewStatus(reviewToken);

    const reviewContent = review.data?.content;
    const isTenantAdminViewer = Boolean(profile.data?.role_codes?.includes("tenant_admin"));
    const isApproved = review.data?.link.status === "approved";
    const displayBrandName = brand?.name || reviewContent?.brand_name || "Brand Name";
    const effectiveTitle = brand?.name || reviewContent?.brand_name || reviewContent?.title || "Violyt";
    const reviewPreviewAssets = resolveReviewDisplayAssets(reviewContent);
    const historyPreviewAssets = resolveReviewDisplayAssets(undefined, latestContent?.assets);
    const previewAssets = reviewPreviewAssets.length ? reviewPreviewAssets : historyPreviewAssets;
    const generationDecision = coerceGenerationDecision(reviewContent?.generation_decision || latestContent?.generation_decision);
    const previewUrl = previewAssets[0]?.asset_url || resolveAssetUrl(previewAssets[0]?.storage_path);
    const activePreviewUrl = previewAssets[activePreviewIndex]?.asset_url || resolveAssetUrl(previewAssets[activePreviewIndex]?.storage_path) || previewUrl;
    const candidateAssets = reviewContent?.assets || latestContent?.assets || [];
    const appOrigin = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";
    const shareUrl = reviewToken ? `${appOrigin}/review/${reviewToken}` : "";
    const accessGrantorName = review.data?.link.created_by_name?.trim() || "Violyt";

    const commentAuthorName = isTenantAdminViewer
        ? profile.data?.full_name || "Tenant Admin"
        : externalMode
            ? reviewerName || "Reviewer"
            : "Frontend Reviewer";

    const comments = (review.data?.comments || []).map((item) => ({
        id: item.id,
        parentCommentId: item.parent_comment_id || null,
        author: item.external_author_name || "Reviewer",
        initials: (item.external_author_name || "R").slice(0, 1).toUpperCase(),
        color: stableCommentColor(item.author_user_id || item.external_author_name || "Reviewer"),
        content: item.body,
        timestamp: "Just now",
    }));
    const repliesByParent = comments.reduce<Record<string, typeof comments>>((grouped, item) => {
        if (item.parentCommentId) {
            grouped[item.parentCommentId] = [...(grouped[item.parentCommentId] || []), item];
        }
        return grouped;
    }, {});
    const topLevelComments = comments.filter((item) => !item.parentCommentId);

    const handleGenerateLink = () => {
        if (!latestContent) {
            return;
        }
        createLink.mutate(
            {
                content_version_id: latestContent.id,
                title: `${effectiveTitle} Review`,
                allow_external_comments: true,
            },
            {
                onSuccess: (response) => {
                    setReviewToken(response.token);
                    setModalMode("share");
                },
            },
        );
    };

    const submitComment = (body: string, parentCommentId?: string | null, onSuccess?: () => void) => {
        if (!body.trim() || !reviewToken) {
            return;
        }
        addComment.mutate(
            {
                body,
                external_author_name: commentAuthorName,
                parent_comment_id: parentCommentId || undefined,
            },
            {
                onSuccess,
            },
        );
    };

    const handleComment = () => {
        submitComment(comment, null, () => setComment(""));
    };

    const handleReply = (parentCommentId: string) => {
        submitComment(replyDrafts[parentCommentId] || "", parentCommentId, () => {
            setReplyDrafts((current) => ({ ...current, [parentCommentId]: "" }));
        });
    };

    const handleApprove = () => {
        if (!reviewToken || isApproved) {
            return;
        }
        updateReviewStatus.mutate({ status: "approved" });
    };

    const handleCopyLink = async () => {
        if (!shareUrl) {
            return;
        }
        await navigator.clipboard.writeText(shareUrl);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
    };

    const exportCandidates = [
        { label: "PDF Standard", icon: FileText, url: resolveAssetUrl(candidateAssets.find((asset) => resolveAssetByExtension(asset.storage_path, ".pdf"))?.storage_path) || previewUrl },
        { label: "JPG", icon: ImageIcon, url: resolveAssetUrl(candidateAssets.find((asset) => resolveAssetByExtension(asset.storage_path, ".jpg") || resolveAssetByExtension(asset.storage_path, ".jpeg"))?.storage_path) || previewUrl },
        { label: "PNG", icon: ImageIcon, url: resolveAssetUrl(candidateAssets.find((asset) => resolveAssetByExtension(asset.storage_path, ".png"))?.storage_path) || previewUrl },
    ];

    const openShareWindow = (url: string) => {
        window.open(url, "_blank", "noopener,noreferrer,width=720,height=720");
    };

    const handleSocialShare = async (network: "instagram" | "facebook" | "linkedin") => {
        if (!shareUrl && !activePreviewUrl) {
            return;
        }
        const target = shareUrl || activePreviewUrl || "";
        if (network === "instagram") {
            if (navigator.share && activePreviewUrl) {
                await navigator.share({ title: effectiveTitle, text: `${effectiveTitle} review`, url: target });
                return;
            }
            await navigator.clipboard.writeText(target);
            openShareWindow("https://www.instagram.com/");
            return;
        }
        if (network === "facebook") {
            openShareWindow(`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(target)}`);
            return;
        }
        openShareWindow(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(target)}`);
    };

    const renderCommentThread = (item: (typeof comments)[number], options?: { paragraphClassName?: string }) => {
        const replyValue = replyDrafts[item.id] || "";
        const replies = repliesByParent[item.id] || [];
        return (
            <div key={item.id} className="space-y-2">
                <div className="space-y-1">
                    <div className="flex items-center justify-between gap-3">
                        <div className="flex min-w-0 items-center gap-2">
                            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[15px] font-semibold text-white" style={{ backgroundColor: item.color }}>
                                {item.initials}
                            </span>
                            <span className="truncate text-[18px] font-medium text-[#252837]">{item.author}</span>
                        </div>
                        <span className="shrink-0 text-[14px] text-[#252837]">2 days ago</span>
                    </div>
                    <p className={options?.paragraphClassName || "text-[18px] leading-[25px] text-[#252837]"}>{item.content}</p>
                </div>

                {replies.length ? (
                    <div className="ml-8 space-y-2 border-l border-[#DADAE0] pl-3">
                        {replies.map((reply) => (
                            <div key={reply.id} className="space-y-1">
                                <div className="flex items-center justify-between gap-3">
                                    <div className="flex min-w-0 items-center gap-2">
                                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[15px] font-semibold text-white" style={{ backgroundColor: reply.color }}>
                                            {reply.initials}
                                        </span>
                                        <span className="truncate text-[18px] font-medium text-[#252837]">{reply.author}</span>
                                    </div>
                                    <span className="shrink-0 text-[14px] text-[#252837]">2 days ago</span>
                                </div>
                                <p className={options?.paragraphClassName || "text-[18px] leading-[25px] text-[#252837]"}>{reply.content}</p>
                            </div>
                        ))}
                    </div>
                ) : null}

                <div className="flex h-[43px] items-center bg-white">
                    <Input
                        value={replyValue}
                        onChange={(event) => setReplyDrafts((current) => ({ ...current, [item.id]: event.target.value }))}
                        placeholder="Reply"
                        className="h-full flex-1 rounded-none border-none bg-transparent px-5 text-[20px] shadow-none placeholder:text-[#252837] focus-visible:ring-0"
                    />
                    <Button
                        onClick={() => handleReply(item.id)}
                        disabled={!replyValue.trim() || addComment.isPending || !reviewToken}
                        className="mr-2 h-8 w-9 rounded-none bg-[#EFEFF2] p-0 text-primary hover:bg-[#E8E7EF]"
                        aria-label="Submit reply"
                    >
                        <SendHorizontal className="h-5 w-5 rotate-[-45deg]" />
                    </Button>
                </div>
            </div>
        );
    };

    if (externalMode && !reviewToken) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-white text-sm text-[#777777]">
                Review link is missing.
            </div>
        );
    }

    if (externalMode && (review.isLoading || (hasAuthToken && profile.isLoading))) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-white text-sm text-[#777777]">
                Loading review...
            </div>
        );
    }

    if (externalMode && review.isError) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-white px-6 text-center">
                <div>
                    <h1 className="text-2xl font-semibold text-primary">Review unavailable</h1>
                    <p className="mt-3 text-sm text-[#777777]">We could not load this review link. Please reopen it from Violyt and try again.</p>
                </div>
            </div>
        );
    }

    if (externalMode && isTenantAdminViewer) {
        return (
            <div className="min-h-screen bg-white text-[#1D2130]">
                <header className="flex h-[74px] items-center border-b border-[#D9D9DF] px-9">
                    <div className="flex items-center gap-2.5">
                        <span className="flex h-7 w-7 items-center justify-center rounded-[3px] bg-primary text-lg font-bold leading-none text-white">V</span>
                        <span className="text-[28px] font-extrabold leading-none text-primary">Violyt</span>
                    </div>
                </header>

                <main className="mx-auto min-h-[calc(100vh-74px)] w-full max-w-[886px] px-4 pb-36 pt-10">
                    <div className="mb-9 flex items-center justify-between gap-5 pr-[10px]">
                        <h1 className="text-[32px] font-extrabold leading-none text-primary">{displayBrandName}</h1>
                        <Button
                            type="button"
                            onClick={handleApprove}
                            disabled={isApproved || updateReviewStatus.isPending || !reviewToken}
                            className={`h-[45px] rounded-[4px] px-5 text-[18px] font-medium text-white ${
                                isApproved
                                    ? "bg-[#8E8E8E] hover:bg-[#8E8E8E] disabled:cursor-default disabled:opacity-100"
                                    : "bg-primary hover:bg-primary/90 disabled:opacity-70"
                            }`}
                        >
                            {isApproved ? "Approved" : updateReviewStatus.isPending ? "Approving..." : "Approve"}
                        </Button>
                    </div>

                    <section className="flex items-start gap-[30px]">
                        <div className="flex min-h-[352px] flex-1 flex-col items-center justify-center bg-[#F1F2F6] p-[23px]">
                            <div className="flex h-[302px] w-full max-w-[470px] items-center justify-center overflow-hidden bg-white">
                                {activePreviewUrl ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={activePreviewUrl} alt="Review creative" className="h-full w-full object-contain" />
                                ) : review.isLoading ? (
                                    <div className="text-sm text-[#777777]">Loading preview...</div>
                                ) : (
                                    <div className="text-sm text-[#777777]">No preview available.</div>
                                )}
                            </div>

                            {previewAssets.length > 1 ? (
                                <div className="mt-4 flex max-w-full gap-3 overflow-x-auto pb-1">
                                    {previewAssets.map((asset, index) => {
                                        const thumbnailUrl = asset.asset_url || resolveAssetUrl(asset.storage_path);
                                        if (!thumbnailUrl) {
                                            return null;
                                        }
                                        return (
                                            <button
                                                key={asset.asset_id || asset.storage_path || asset.asset_url || index}
                                                type="button"
                                                onClick={() => setActivePreviewIndex(index)}
                                                className={`h-14 w-14 shrink-0 border bg-white p-1 ${index === activePreviewIndex ? "border-primary" : "border-transparent hover:border-[#D9DDE8]"}`}
                                                aria-label={`Show slide ${index + 1}`}
                                            >
                                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                                <img src={thumbnailUrl} alt={`Review slide ${index + 1}`} className="h-full w-full object-cover" />
                                            </button>
                                        );
                                    })}
                                </div>
                            ) : null}
                        </div>

                        <aside className="relative min-h-[352px] w-[320px] shrink-0 bg-[#F7F7F8] px-3 pb-6 pt-3">
                            <CommentBubbleIcon className="absolute -left-[31px] -top-[30px] h-8 w-8 shadow-sm" />
                            <div className="mb-3 border-b border-[#CFCFD5] pb-3 pl-1">
                                <h2 className="text-[20px] font-medium text-[#252837]">Comment</h2>
                            </div>

                            <div className="max-h-[202px] space-y-5 overflow-y-auto pr-1">
                                {topLevelComments.length ? topLevelComments.map((item) => renderCommentThread(item)) : (
                                    <p className="py-8 text-center text-sm text-[#777777]">No comments yet.</p>
                                )}
                            </div>

                            <Input
                                value={comment}
                                onChange={(event) => setComment(event.target.value)}
                                placeholder="Add your comment"
                                className="mt-3 h-[43px] rounded-[4px] border-none bg-white text-center text-[20px] shadow-none placeholder:text-[#252837] focus-visible:ring-1 focus-visible:ring-primary"
                            />
                        </aside>
                    </section>

                    <div className="fixed bottom-[58px] left-1/2 w-[790px] max-w-[calc(100vw-48px)] -translate-x-1/2 bg-white shadow-[0_18px_36px_-24px_rgba(60,47,143,0.5)]">
                        <div className="flex h-[67px] items-center border border-[#E0E3ED] px-5">
                            <Input
                                value={comment}
                                onChange={(event) => setComment(event.target.value)}
                                placeholder="Add your comment"
                                className="h-full flex-1 border-none bg-transparent text-[20px] shadow-none placeholder:text-[#787792] focus-visible:ring-0"
                            />
                            <Button
                                onClick={handleComment}
                                disabled={!comment.trim() || addComment.isPending || !reviewToken}
                                className="h-9 w-10 rounded-none bg-[#EFEFF2] p-0 text-primary hover:bg-[#E8E7EF]"
                                aria-label="Submit comment"
                            >
                                <SendHorizontal className="h-5 w-5 rotate-[-45deg]" />
                            </Button>
                        </div>
                    </div>
                    <p className="fixed bottom-5 left-1/2 -translate-x-1/2 text-center text-base text-[#A0A0A7]">
                        Violyt suggestions may need review. Verify accuracy before use.
                    </p>
                </main>
            </div>
        );
    }

    if (externalMode && !reviewerName) {
        return (
            <div className="relative min-h-screen bg-white px-6">
                <div className="absolute left-9 top-9 flex items-center gap-2.5">
                    <span className="flex h-7 w-7 items-center justify-center rounded-[3px] bg-primary text-lg font-bold leading-none text-white">V</span>
                    <span className="text-[28px] font-extrabold leading-none text-primary">Violyt</span>
                </div>
                <div className="mx-auto flex min-h-screen w-full max-w-[430px] flex-col items-center justify-center pt-4 text-center">
                    <div className="mb-10 flex h-[66px] w-[66px] items-center justify-center rounded-[6px] bg-primary text-[46px] font-extrabold leading-none text-white shadow-[0_16px_34px_-24px_rgba(63,49,146,0.9)]">V</div>
                    <h1 className="text-[48px] font-extrabold leading-tight tracking-[0] text-[#121212]">Welcome to Violyt</h1>
                    <p className="mt-3 text-base font-medium text-[#4B4B4B]">{accessGrantorName} has given you access!</p>
                    <div className="mt-12 w-full space-y-3 text-left">
                        <label className="text-base font-semibold text-[#121212]">Your Name</label>
                        <Input
                            value={welcomeName}
                            onChange={(event) => setWelcomeName(event.target.value)}
                            placeholder="Enter your name"
                            className="h-12 rounded-[10px] border-none bg-[#F3F4F8] px-4 text-sm shadow-none placeholder:text-[#777777] focus-visible:ring-1 focus-visible:ring-primary"
                        />
                    </div>
                    <Button
                        onClick={() => setReviewerName(welcomeName.trim())}
                        disabled={!welcomeName.trim()}
                        className="mt-10 h-12 w-full rounded-none bg-primary text-base font-medium text-white hover:bg-primary/90"
                    >
                        Continue
                    </Button>
                </div>
            </div>
        );
    }

    if (externalMode) {
        return (
            <div className="min-h-screen bg-white text-[#1D2130]">
                <aside className="fixed inset-y-0 left-0 z-20 flex w-[290px] flex-col border-r border-[#D9D9DF] bg-white px-[30px] py-8">
                    <div className="flex items-center justify-between">
                        <span className="text-[32px] font-extrabold leading-none text-primary">Violyt</span>
                        <PanelLeftClose className="h-4 w-4 text-primary" />
                    </div>

                    <nav className="mt-12 space-y-7 text-[20px] text-[#666666]">
                        <div className="flex items-center gap-3">
                            <Home className="h-5 w-5" />
                            <span>Dashboard</span>
                        </div>
                        <div className="flex items-center justify-between gap-3">
                            <span className="flex items-center gap-3">
                                <Grid2X2 className="h-5 w-5" />
                                <span>Brand Spaces</span>
                            </span>
                            <span className="text-lg leading-none">⌄</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <Folder className="h-5 w-5" />
                            <span>{displayBrandName}</span>
                        </div>
                        <div className="flex items-center gap-3 pt-3">
                            <Bell className="h-5 w-5" />
                            <span>Notification</span>
                        </div>
                    </nav>

                    <div className="mt-auto flex items-center gap-3">
                        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#52B2CF] text-lg font-semibold text-white">
                            {(reviewerName || displayBrandName || "P").slice(0, 1).toUpperCase()}
                        </span>
                        <span className="text-[20px] font-semibold text-[#121212]">{displayBrandName}</span>
                    </div>
                </aside>

                <main className="ml-[290px] min-h-screen pb-28">
                    <header className="flex h-[92px] items-center border-b border-[#D9D9DF] px-6">
                        <h1 className="text-[34px] font-extrabold leading-none text-primary">{displayBrandName}</h1>
                    </header>

                    <section className="px-6 pt-8">
                        <div className="flex max-w-[870px] items-start gap-6">
                            <div className="flex min-h-[352px] flex-1 items-center justify-center bg-[#F1F2F6] p-6">
                                <div className="flex h-[302px] w-full max-w-[470px] items-center justify-center overflow-hidden bg-white">
                                    {activePreviewUrl ? (
                                        // eslint-disable-next-line @next/next/no-img-element
                                        <img src={activePreviewUrl} alt="Review creative" className="h-full w-full object-contain" />
                                    ) : review.isLoading ? (
                                        <div className="text-sm text-[#777777]">Loading preview...</div>
                                    ) : (
                                        <div className="text-sm text-[#777777]">No preview available.</div>
                                    )}
                                </div>
                            </div>

                            <aside className="relative w-[320px] bg-[#F7F7F8] px-3 pb-6 pt-3">
                                <CommentBubbleIcon className="absolute -left-[26px] -top-1 h-8 w-8 shadow-sm" />
                                <div className="mb-3 border-b border-[#CFCFD5] pb-3 pl-1">
                                    <h2 className="text-[20px] font-medium text-[#252837]">Comment</h2>
                                </div>

                                <div className="max-h-[185px] space-y-5 overflow-y-auto pr-1">
                                    {topLevelComments.length ? topLevelComments.map((item) => renderCommentThread(item, { paragraphClassName: "pl-0 text-[18px] leading-[25px] text-[#252837]" })) : (
                                        <p className="py-5 text-center text-sm text-[#777777]">No comments yet.</p>
                                    )}
                                </div>

                                <div className="mt-3 space-y-3">
                                    <Input
                                        value={comment}
                                        onChange={(event) => setComment(event.target.value)}
                                        placeholder="Add your comment"
                                        className="h-[43px] rounded-[4px] border-none bg-white text-center text-[20px] shadow-none placeholder:text-[#252837] focus-visible:ring-1 focus-visible:ring-primary"
                                    />
                                    <div className="flex justify-center">
                                        <Button
                                            onClick={handleComment}
                                            disabled={!comment.trim() || addComment.isPending || !reviewToken}
                                            className="h-[45px] rounded-[4px] bg-primary px-5 text-[18px] font-medium text-white hover:bg-primary/90"
                                        >
                                            Confirm
                                        </Button>
                                    </div>
                                </div>
                            </aside>
                        </div>
                    </section>

                    <div className="fixed bottom-[66px] left-[314px] w-[790px] bg-white shadow-[0_18px_36px_-24px_rgba(60,47,143,0.5)]">
                        <div className="flex h-[67px] items-center border border-[#E0E3ED] px-5">
                            <Input
                                value={comment}
                                onChange={(event) => setComment(event.target.value)}
                                placeholder="Add your comment"
                                className="h-full flex-1 border-none bg-transparent text-[20px] shadow-none placeholder:text-[#787792] focus-visible:ring-0"
                            />
                            <Button
                                onClick={handleComment}
                                disabled={!comment.trim() || addComment.isPending || !reviewToken}
                                className="h-9 w-10 rounded-none bg-[#EFEFF2] p-0 text-primary hover:bg-[#E8E7EF]"
                                aria-label="Submit comment"
                            >
                                <SendHorizontal className="h-5 w-5 rotate-[-45deg]" />
                            </Button>
                        </div>
                    </div>
                    <p className="fixed bottom-6 left-[470px] text-center text-base text-[#A0A0A7]">
                        Violyt suggestions may need review. Verify accuracy before use.
                    </p>
                </main>
            </div>
        );
    }

    return (
        <div className="min-h-[calc(100vh-10vh)] bg-white">
            <ReviewImageViewer
                assets={previewAssets}
                activeIndex={activePreviewIndex}
                onActiveIndexChange={setActivePreviewIndex}
                onSave={() => setModalMode("save")}
                onShare={reviewToken ? () => setModalMode("share") : handleGenerateLink}
                onClose={() => {
                    if (window.history.length > 1) {
                        window.history.back();
                    }
                }}
            />

            <div className="mx-auto max-w-5xl px-4 pb-8">
                {generationDecision ? (
                    <div className="mb-4 rounded-[4px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
                        <div className="flex flex-wrap items-center gap-2">
                            <span className="bg-primary/8 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-primary">
                                {formatGenerationMode(generationDecision.mode)}
                            </span>
                            {getGenerationDecisionTemplate(generationDecision) ? (
                                <span className="text-xs font-medium text-slate-500">
                                    Template: {getGenerationDecisionTemplate(generationDecision)}
                                </span>
                            ) : null}
                        </div>
                        {getGenerationDecisionReasons(generationDecision).length ? (
                            <p className="mt-2 text-sm leading-6 text-slate-600">
                                {getGenerationDecisionReasons(generationDecision)[0]}
                            </p>
                        ) : null}
                    </div>
                ) : null}

                {topLevelComments.length ? (
                    <SurfaceCard className="mb-4 space-y-3 border border-[#E5E7F0] bg-white p-4 shadow-none">
                        <p className="text-base font-semibold text-[#121212]">Comment</p>
                        {topLevelComments.map((item) => renderCommentThread(item, { paragraphClassName: "mt-1 text-sm leading-6 text-slate-600" }))}
                    </SurfaceCard>
                ) : null}

                <SurfaceCard className="mx-auto flex items-center gap-3 border border-[#E1E4ED] bg-white px-4 py-3 shadow-[0_18px_36px_-28px_rgba(60,47,143,0.45)]">
                    <Input
                        placeholder="Add your comment"
                        className="h-10 border-none bg-transparent text-sm shadow-none focus-visible:ring-0"
                        value={comment}
                        onChange={(event) => setComment(event.target.value)}
                    />
                    <Button
                        className="h-10 w-10 rounded-none bg-primary p-0 hover:bg-primary/90"
                        onClick={handleComment}
                        disabled={!comment.trim() || addComment.isPending || !reviewToken}
                    >
                        <SendHorizontal className="h-4 w-4" />
                    </Button>
                </SurfaceCard>
            </div>

            <p className="w-full absolute bottom-0 pb-1 mx-auto text-center text-sm text-[#A0A0A7]">Violyt suggestions may need review. Verify accuracy before use.</p>

            {modalMode !== "none" ? (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#121212]/75 px-4">
                    <div className={`relative w-full bg-white p-8 shadow-2xl ${modalMode === "share" ? "max-w-[466px]" : "max-w-[466px]"}`}>
                        <div className="absolute right-3 top-3">
                            <button type="button" onClick={() => setModalMode("none")} className="flex h-7 w-7 items-center justify-center rounded-full bg-[#F7F7F8] text-[#121212]">
                                <X className="h-4 w-4" />
                            </button>
                        </div>

                        {modalMode === "share" ? (
                            <div className="space-y-4 bg-[#F6F6F7] p-4">
                                <h2 className="text-2xl font-semibold text-[#121212]">Share</h2>
                                {activePreviewUrl ? (
                                    <div className="relative">
                                        {/* eslint-disable-next-line @next/next/no-img-element */}
                                        <img src={activePreviewUrl} alt="Share preview" className="max-h-[260px] w-full object-cover" />
                                        <button
                                            type="button"
                                            onClick={() => activePreviewUrl && window.open(activePreviewUrl, "_blank", "noopener,noreferrer")}
                                            className="absolute right-3 top-3 flex h-9 w-9 items-center justify-center rounded-full bg-white text-[#121212] shadow"
                                        >
                                            <Download className="h-5 w-5" />
                                        </button>
                                    </div>
                                ) : null}
                                <div className="flex justify-center">
                                    <Button onClick={handleCopyLink} className="h-10 rounded-none bg-primary px-8 text-lg hover:bg-primary/90">
                                        <Copy className="mr-3 h-5 w-5" />
                                        {copied ? "Copied" : "Copy Link"}
                                    </Button>
                                </div>
                                <div className="border-t border-slate-200 pt-6 text-center">
                                    <p className="text-lg font-medium text-[#121212]">Social Media</p>
                                    <div className="mt-4 flex justify-center gap-5">
                                        <button
                                            type="button"
                                            onClick={() => void handleSocialShare("instagram")}
                                            className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-primary shadow-sm"
                                        >
                                            <Instagram className="h-5 w-5" />
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => void handleSocialShare("facebook")}
                                            className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-primary shadow-sm"
                                        >
                                            <Facebook className="h-5 w-5" />
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => void handleSocialShare("linkedin")}
                                            className="flex h-9 w-9 items-center justify-center rounded-full bg-white text-primary shadow-sm"
                                        >
                                            <Linkedin className="h-5 w-5" />
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="space-y-6 bg-[#F6F6F7] p-10">
                                <h2 className="text-2xl font-semibold text-[#121212]">Save as</h2>
                                <div className="bg-white px-6 shadow-[0_18px_36px_-28px_rgba(60,47,143,0.45)]">
                                    {exportCandidates.map((item) => (
                                        <button
                                            key={item.label}
                                            type="button"
                                            onClick={() => item.url && window.open(item.url, "_blank", "noopener,noreferrer")}
                                            className="flex w-full items-center gap-4 border-b border-slate-100 py-4 text-left last:border-none"
                                        >
                                            <item.icon className="h-5 w-5 text-[#121212]" />
                                            <span className="text-lg font-normal text-[#4B4B4B]">{item.label}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ) : null}
        </div>
    );
}
