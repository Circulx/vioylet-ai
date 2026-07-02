"use client";

import { Copy, Download, Facebook, FileText, Image as ImageIcon, Instagram, Linkedin, SendHorizontal, Share2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SurfaceCard } from "@/components/common/DesignPrimitives";
import { resolveBrandByRouteKey } from "@/lib/brand-routing";
import { apiOrigin } from "@/lib/env";
import { useBrands } from "@/hooks/useBrands";
import { useAddReviewComment, useContentHistory, useCreateShareLink, useReviewDetail } from "@/hooks/useContentWorkspace";
import type { AssetReference } from "@/lib/api/contracts";
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
    const [reviewerName, setReviewerName] = useState("");
    const [welcomeName, setWelcomeName] = useState("");
    const [modalMode, setModalMode] = useState<ModalMode>("none");
    const [copied, setCopied] = useState(false);
    const [activePreviewIndex, setActivePreviewIndex] = useState(0);

    const { data: brands } = useBrands(Boolean(brandKey) && !externalMode);
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

    const reviewContent = review.data?.content;
    const effectiveTitle = brand?.name || reviewContent?.title || "Violyt";
    const findDisplayAssets = (assets?: AssetReference[]) => {
        if (!assets?.length) {
            return [];
        }
        const exportImages = assets.filter(
            (asset) => asset.mime_type.startsWith("image/") && asset.asset_role === "render_export",
        );
        if (exportImages.length) {
            return dedupeAssets(exportImages);
        }
        const previewImages = assets.filter(
            (asset) => asset.mime_type.startsWith("image/") && asset.asset_role === "render_preview",
        );
        if (previewImages.length) {
            return dedupeAssets(previewImages);
        }
        return dedupeAssets(assets.filter((asset) => asset.mime_type.startsWith("image/")));
    };
    const reviewPreviewAssets = findDisplayAssets(reviewContent?.assets);
    const historyPreviewAssets = findDisplayAssets(latestContent?.assets);
    const previewAssets = reviewPreviewAssets.length ? reviewPreviewAssets : historyPreviewAssets;
    const generationDecision = coerceGenerationDecision(reviewContent?.generation_decision || latestContent?.generation_decision);
    const previewUrl = previewAssets[0]?.asset_url || resolveAssetUrl(previewAssets[0]?.storage_path);
    const activePreviewUrl = previewAssets[activePreviewIndex]?.asset_url || resolveAssetUrl(previewAssets[activePreviewIndex]?.storage_path) || previewUrl;
    const candidateAssets = reviewContent?.assets || latestContent?.assets || [];
    const appOrigin = typeof window !== "undefined" ? window.location.origin : "http://localhost:3000";
    const shareUrl = reviewToken ? `${appOrigin}/review/${reviewToken}` : "";

    const comments = (review.data?.comments || []).map((item) => ({
        id: item.id,
        author: item.external_author_name || "Reviewer",
        initials: (item.external_author_name || "R").slice(0, 1).toUpperCase(),
        color: "#52B2CF",
        content: item.body,
        timestamp: "Just now",
    }));

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

    const handleComment = () => {
        if (!comment.trim() || !reviewToken) {
            return;
        }
        addComment.mutate(
            {
                body: comment,
                external_author_name: externalMode ? reviewerName || "Reviewer" : "Frontend Reviewer",
            },
            {
                onSuccess: () => setComment(""),
            },
        );
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

    if (externalMode && !reviewerName) {
        return (
            <div className="flex min-h-[calc(100vh-10vh)] items-center justify-center bg-green-300 px-6">
                <div className="w-full max-w-md text-center">
                    <div className="mx-auto mb-8 flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-3xl font-bold text-white">V</div>
                    <h1 className="font-dmSans text-5xl font-extrabold text-slate-900">Welcome to Violyt</h1>
                    <p className="mt-3 text-slate-500">A reviewer has given you access.</p>
                    <div className="mt-12 space-y-3 text-left">
                        <label className="text-base font-medium text-slate-700">Your Name</label>
                        <Input
                            value={welcomeName}
                            onChange={(event) => setWelcomeName(event.target.value)}
                            placeholder="Enter your name"
                            className="h-12 border-none bg-input-field shadow-none"
                        />
                    </div>
                    <Button
                        onClick={() => setReviewerName(welcomeName.trim())}
                        disabled={!welcomeName.trim()}
                        className="mt-8 h-12 w-full rounded-none bg-primary text-base hover:bg-primary/90"
                    >
                        Continue
                    </Button>
                </div>
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

                {comments.length ? (
                    <SurfaceCard className="mb-4 space-y-3 border border-[#E5E7F0] bg-white p-4 shadow-none">
                        <p className="text-base font-semibold text-[#121212]">Comment</p>
                        {comments.map((item) => (
                            <div key={item.id} className="border-b border-slate-100 pb-3 last:border-none last:pb-0">
                                <div className="flex items-start justify-between gap-3">
                                    <div className="flex items-start gap-3">
                                        <span className="mt-1 flex h-7 w-7 items-center justify-center rounded-full text-sm font-semibold text-white" style={{ backgroundColor: item.color }}>
                                            {item.initials}
                                        </span>
                                        <div>
                                            <p className="font-semibold text-slate-800">{item.author}</p>
                                            <p className="mt-1 text-sm leading-6 text-slate-600">{item.content}</p>
                                        </div>
                                    </div>
                                    <span className="text-xs text-slate-400">{item.timestamp}</span>
                                </div>
                            </div>
                        ))}
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
