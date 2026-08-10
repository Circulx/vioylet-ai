"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Loader2,
  Image as ImageIcon,
  CheckCircle2,
  Download,
  ChevronLeft,
  ChevronRight,
  Pencil,
  X,
} from "lucide-react";
import { SurfaceCard } from "@/components/common/DesignPrimitives";
import BlueprintApprovalCard from "@/components/brandSpaces/tabs/BlueprintApprovalCard";
import PostCaptionBlock from "@/components/chat/PostCaptionBlock";
import type { CreativeBlueprintResponse } from "@/lib/api/contracts";
import { buildPostCaption } from "@/lib/post-caption";
import { usePipeline } from "@/hooks/usePipeline";
import { apiOrigin } from "@/lib/env";
import { cn } from "@/lib/utils";

export type ChatPipelineStatus =
  | "idle"
  | "running"
  | "awaiting_blueprint_approval"
  | "generating"
  | "complete"
  | "failed"
  | "cancelled";

export type ChatPipelineState = {
  status: ChatPipelineStatus;
  runId?: string;
  prompt?: string;
  format?: string;
  platform?: string;
  blueprint?: CreativeBlueprintResponse | null;
  imageUrls?: string[];
  error?: string | null;
};

type EditableFields = {
  headline: string;
  supporting_line: string;
  body: string;
  cta: string;
};

type Props = {
  state: ChatPipelineState;
  isApproving?: boolean;
  onApprove: (edited: CreativeBlueprintResponse) => void;
  onCancel: () => void;
  onImagesChange?: (urls: string[], fields?: EditableFields, imageIndex?: number) => void;
};

function resolveUrl(path: string) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${apiOrigin}${path.startsWith("/") ? path : `/${path}`}`;
}

async function downloadImage(path: string, filename: string) {
  const url = resolveUrl(path);
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Download failed (${res.status})`);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
  } catch {
    window.open(url, "_blank", "noopener,noreferrer");
  }
}

function fieldsFromBlueprint(
  blueprint: CreativeBlueprintResponse | null | undefined,
  format: string | undefined,
  imageIndex: number,
): EditableFields {
  if (!blueprint) {
    return { headline: "", supporting_line: "", body: "", cta: "" };
  }
  if (format === "carousel" && blueprint.slides?.length) {
    const slide = blueprint.slides[Math.min(imageIndex, blueprint.slides.length - 1)];
    return {
      headline: slide?.headline || "",
      supporting_line: slide?.supporting_line || "",
      body: slide?.body || "",
      cta: slide?.cta || blueprint.cta || "",
    };
  }
  return {
    headline: blueprint.headline || blueprint.title || "",
    supporting_line: blueprint.supporting_line || "",
    body: blueprint.body || "",
    cta: blueprint.cta || "",
  };
}

function ImageCarousel({
  urls,
  formatLabel,
  blueprint,
  onImagesChange,
}: {
  urls: string[];
  formatLabel?: string;
  blueprint?: CreativeBlueprintResponse | null;
  onImagesChange?: (urls: string[], fields?: EditableFields, imageIndex?: number) => void;
}) {
  const { editImageText, isEditingImage } = usePipeline();
  const [index, setIndex] = useState(0);
  const [editing, setEditing] = useState(false);
  const [fields, setFields] = useState<EditableFields>({
    headline: "",
    supporting_line: "",
    body: "",
    cta: "",
  });
  const [editError, setEditError] = useState<string | null>(null);

  const total = urls.length;
  const current = urls[Math.min(index, Math.max(total - 1, 0))] || "";

  useEffect(() => {
    setIndex(0);
  }, [urls.join("|")]);

  useEffect(() => {
    if (!editing) {
      setFields(fieldsFromBlueprint(blueprint, formatLabel, index));
    }
  }, [blueprint, formatLabel, index, editing]);

  const goPrev = useCallback(() => {
    setEditing(false);
    setIndex((i) => (i <= 0 ? total - 1 : i - 1));
  }, [total]);

  const goNext = useCallback(() => {
    setEditing(false);
    setIndex((i) => (i >= total - 1 ? 0 : i + 1));
  }, [total]);

  const handleDownload = useCallback(() => {
    const ext = current.includes(".jpg") || current.includes(".jpeg") ? "jpg" : "png";
    void downloadImage(current, `violyt-creative-${index + 1}.${ext}`);
  }, [current, index]);

  const openEdit = () => {
    setEditError(null);
    setFields(fieldsFromBlueprint(blueprint, formatLabel, index));
    setEditing(true);
  };

  const handleSave = async () => {
    if (!current) return;
    setEditError(null);
    try {
      const result = await editImageText.mutateAsync({
        image_url: current,
        headline: fields.headline,
        supporting_line: fields.supporting_line,
        body: fields.body,
        cta: fields.cta,
      });
      const next = [...urls];
      next[index] = result.image_url;
      onImagesChange?.(next, fields, index);
      setEditing(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Could not save text edits.";
      setEditError(msg);
    }
  };

  if (!current) return null;

  const isMulti = total > 1;
  const counterLabel =
    formatLabel === "carousel"
      ? `Slide ${index + 1} of ${total}`
      : `${index + 1} of ${total}`;

  return (
    <div className="space-y-3">
      <div className="overflow-hidden rounded-xl border border-emerald-100 bg-white">
        <div className="relative">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={resolveUrl(current)}
            alt={`Generated creative ${index + 1}`}
            className="h-auto w-full"
          />

          {isMulti ? (
            <>
              <button
                type="button"
                onClick={goPrev}
                aria-label="Previous image"
                className="absolute left-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-white/80 bg-white/90 text-[#121212] shadow-sm backdrop-blur-sm transition hover:bg-white"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={goNext}
                aria-label="Next image"
                className="absolute right-2 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-white/80 bg-white/90 text-[#121212] shadow-sm backdrop-blur-sm transition hover:bg-white"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full bg-black/55 px-3 py-1 text-[11px] font-medium text-white backdrop-blur-sm">
                {counterLabel}
              </div>
            </>
          ) : null}
        </div>

        <div className="flex items-center justify-between gap-2 border-t border-emerald-50 px-3 py-2">
          {isMulti ? (
            <div className="flex items-center gap-1.5">
              {urls.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  aria-label={`Go to image ${i + 1}`}
                  onClick={() => {
                    setEditing(false);
                    setIndex(i);
                  }}
                  className={cn(
                    "h-1.5 rounded-full transition-all",
                    i === index ? "w-4 bg-emerald-600" : "w-1.5 bg-emerald-200 hover:bg-emerald-300",
                  )}
                />
              ))}
            </div>
          ) : (
            <span />
          )}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={openEdit}
              className="inline-flex h-8 items-center gap-1.5 border border-emerald-200 bg-white px-3 text-[11px] font-medium text-emerald-800 hover:bg-emerald-50"
            >
              <Pencil className="h-3.5 w-3.5" />
              Edit text
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="inline-flex h-8 items-center gap-1.5 border border-emerald-200 bg-white px-3 text-[11px] font-medium text-emerald-800 hover:bg-emerald-50"
            >
              <Download className="h-3.5 w-3.5" />
              Download{isMulti ? ` ${index + 1}` : ""}
            </button>
          </div>
        </div>
      </div>

      {editing ? (
        <div className="space-y-3 rounded-xl border border-[#E8EAF0] bg-white p-4">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-[#121212]">Fix text / spelling</p>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="inline-flex h-7 w-7 items-center justify-center text-[#6A6E8B] hover:text-[#121212]"
              aria-label="Close editor"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <p className="text-[11px] text-[#6A6E8B]">
            Correct any misspelled words, then Save. The logo corner is left untouched.
          </p>
          <label className="block space-y-1">
            <span className="text-[11px] font-medium text-[#6A6E8B]">Headline</span>
            <input
              value={fields.headline}
              onChange={(e) => setFields((f) => ({ ...f, headline: e.target.value }))}
              className="h-9 w-full border border-[#E8EAF0] bg-[#F7F8FB] px-3 text-sm text-[#121212] outline-none focus:border-emerald-300"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[11px] font-medium text-[#6A6E8B]">Supporting line</span>
            <input
              value={fields.supporting_line}
              onChange={(e) => setFields((f) => ({ ...f, supporting_line: e.target.value }))}
              className="h-9 w-full border border-[#E8EAF0] bg-[#F7F8FB] px-3 text-sm text-[#121212] outline-none focus:border-emerald-300"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[11px] font-medium text-[#6A6E8B]">Body</span>
            <textarea
              value={fields.body}
              onChange={(e) => setFields((f) => ({ ...f, body: e.target.value }))}
              rows={4}
              className="w-full resize-y border border-[#E8EAF0] bg-[#F7F8FB] px-3 py-2 text-sm text-[#121212] outline-none focus:border-emerald-300"
            />
          </label>
          <label className="block space-y-1">
            <span className="text-[11px] font-medium text-[#6A6E8B]">CTA</span>
            <input
              value={fields.cta}
              onChange={(e) => setFields((f) => ({ ...f, cta: e.target.value }))}
              className="h-9 w-full border border-[#E8EAF0] bg-[#F7F8FB] px-3 text-sm text-[#121212] outline-none focus:border-emerald-300"
            />
          </label>
          {editError ? <p className="text-xs text-red-600">{editError}</p> : null}
          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setEditing(false)}
              disabled={isEditingImage}
              className="h-9 border border-[#E8EAF0] bg-white px-4 text-xs font-medium text-[#6A6E8B] hover:bg-[#F7F8FB]"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={isEditingImage}
              className="inline-flex h-9 items-center gap-1.5 bg-emerald-700 px-4 text-xs font-medium text-white hover:bg-emerald-800 disabled:opacity-60"
            >
              {isEditingImage ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
              Save
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function ChatPipelinePanel({
  state,
  isApproving,
  onApprove,
  onCancel,
  onImagesChange,
}: Props) {
  const completeUrls = useMemo(() => state.imageUrls || [], [state.imageUrls]);
  const postCaption = useMemo(
    () =>
      buildPostCaption({
        platform: state.platform || "instagram",
        blueprint: state.blueprint,
      }),
    [state.blueprint, state.platform],
  );

  if (state.status === "idle" || state.status === "cancelled") {
    return null;
  }

  return (
    <div className="mr-auto w-full max-w-[720px] space-y-4 px-3">
      {(state.status === "running" || state.status === "generating") && (
        <SurfaceCard className="border-[#E8EAF0] bg-[#F7F8FB] p-5">
          <div className="flex items-start gap-3">
            <Loader2 className="mt-0.5 h-5 w-5 animate-spin text-primary" />
            <div className="space-y-1">
              <p className="text-sm font-semibold text-[#121212]">
                {state.status === "running"
                  ? "Violyt Intelligence Pipeline is running…"
                  : "Generating finished AI creative…"}
              </p>
              <p className="text-xs text-[#6A6E8B]">
                {state.status === "running"
                  ? "Preparing your creative brief and blueprint. Usually 3–6 minutes — please keep this tab open."
                  : "Creating your AI image with approved text baked in (usually 1–2 minutes)…"}
              </p>
            </div>
          </div>
        </SurfaceCard>
      )}

      {state.status === "awaiting_blueprint_approval" && state.blueprint ? (
        <BlueprintApprovalCard
          blueprint={state.blueprint}
          format={state.format || state.blueprint.format || "static"}
          isApproving={isApproving}
          onApprove={onApprove}
          onCancel={onCancel}
        />
      ) : null}

      {state.status === "complete" && completeUrls.length > 0 ? (
        <SurfaceCard className="space-y-3 border-emerald-100 bg-emerald-50/30 p-4">
          <div className="flex items-center justify-between gap-2 text-emerald-800">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              <p className="text-sm font-semibold">Creative ready</p>
            </div>
            {completeUrls.length > 1 ? (
              <p className="text-[11px] font-medium text-emerald-700/80">
                {completeUrls.length} images — use arrows to browse
              </p>
            ) : null}
          </div>
          {(state.blueprint?.layout_type || state.blueprint?.layout_archetype) && (
            <p className="text-[11px] text-emerald-800/90">
              Layout:{" "}
              <span className="font-semibold">
                {state.blueprint.layout_type || state.blueprint.layout_archetype}
              </span>
              {state.blueprint.source_footer
                ? ` · ${state.blueprint.source_footer}`
                : ""}
            </p>
          )}
          <ImageCarousel
            urls={completeUrls}
            formatLabel={state.format}
            blueprint={state.blueprint}
            onImagesChange={onImagesChange}
          />
          <PostCaptionBlock caption={postCaption} platform={state.platform} />
          {(state.blueprint?.sources?.length ?? 0) > 0 ? (
            <div className="rounded-lg border border-emerald-100 bg-white/70 p-3 space-y-1">
              <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-800">
                Sources
              </p>
              <ul className="space-y-1">
                {(state.blueprint?.sources || []).map((src, i) => {
                  const url = (src.url || "").trim();
                  const isHttp = /^https?:\/\//i.test(url);
                  return (
                  <li key={`${url}-${i}`} className="text-xs text-slate-700 break-all">
                    {isHttp ? (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-emerald-800 underline underline-offset-2 hover:text-emerald-950"
                      >
                        {src.title || url}
                      </a>
                    ) : (
                      <span>{src.title || url || "—"}</span>
                    )}
                  </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
        </SurfaceCard>
      ) : null}

      {state.status === "complete" && !completeUrls.length ? (
        <SurfaceCard className="border-amber-100 bg-amber-50/40 p-4 text-sm text-amber-900">
          <div className="flex items-center gap-2">
            <ImageIcon className="h-4 w-4" />
            Pipeline finished, but no image URL was returned.
          </div>
        </SurfaceCard>
      ) : null}

      {state.status === "failed" ? (
        <SurfaceCard className={cn("border-red-100 bg-red-50/50 p-4 text-sm text-red-700")}>
          {state.error || "Pipeline failed. Try again."}
        </SurfaceCard>
      ) : null}
    </div>
  );
}
