"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { SurfaceCard } from "@/components/common/DesignPrimitives";
import { CheckCircle2, Loader2, XCircle, LayoutTemplate } from "lucide-react";
import type { CreativeBlueprintResponse } from "@/lib/api/contracts";

type Props = {
  blueprint: CreativeBlueprintResponse;
  format: string;
  isApproving?: boolean;
  onApprove: (edited: CreativeBlueprintResponse) => void;
  onCancel: () => void;
};

function Field({
  label,
  value,
  onChange,
  rows = 2,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  rows?: number;
}) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] font-bold uppercase tracking-wide text-amber-700">{label}</label>
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        className="bg-white border-amber-100 text-sm min-h-0"
      />
    </div>
  );
}

export default function BlueprintApprovalCard({
  blueprint,
  format,
  isApproving,
  onApprove,
  onCancel,
}: Props) {
  const [draft, setDraft] = useState<CreativeBlueprintResponse>(blueprint);

  useEffect(() => {
    setDraft(blueprint);
  }, [blueprint]);

  const fmt = (draft.format || format || "static").toLowerCase();
  const headlineReady = Boolean((draft.headline || "").trim());
  const hasPlaceholderSections = (draft.sections || []).some((sec) => {
    const label = (sec.section_label || "").trim().toLowerCase();
    return !label || label === "item" || /^item\s+\d+$/i.test(label);
  });
  const storylineReady =
    (draft.story_flow || []).some((line) => Boolean(String(line || "").trim())) ||
    (draft.sections || []).some((sec) => Boolean((sec.body || "").trim()) || (sec.includes || []).length > 0);
  const blockApprove = !headlineReady || (fmt !== "carousel" && hasPlaceholderSections && !storylineReady);
  const blockReason = !headlineReady
    ? "Add a headline before generating."
    : hasPlaceholderSections && !storylineReady
      ? "Fill section labels/body (no empty Item placeholders) before generating."
      : "";

  return (
    <SurfaceCard className="p-6 border-amber-200 bg-amber-50/40 space-y-5 col-span-1 md:col-span-2">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="bg-amber-100 p-2 rounded-lg">
            <LayoutTemplate className="h-5 w-5 text-amber-700" />
          </div>
          <div>
            <h4 className="font-bold text-amber-950 text-sm">L7c: Creative Blueprint — Approval Required</h4>
            <p className="text-[10px] text-amber-700 font-medium">
              Every LLM mistake is auto-checked &amp; fixed first (names, typos, teasers, layout, sources).
              You review the cleaned draft — same text bakes into the AI image (Brand Space logo only)
            </p>
          </div>
        </div>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-amber-200 text-amber-900">
          {fmt}
        </span>
      </div>

      {(draft.layout_type || draft.layout_archetype) && (
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-md bg-white border border-amber-100 px-2 py-1 font-semibold text-amber-900">
            Layout: {draft.layout_type || draft.layout_archetype}
          </span>
          {draft.source_footer ? (
            <span className="rounded-md bg-white border border-amber-100 px-2 py-1 text-slate-700">
              {draft.source_footer}
            </span>
          ) : null}
        </div>
      )}

      {(draft.sources?.length ?? 0) > 0 && (
        <div className="bg-white/90 rounded-lg border border-amber-100 p-3 space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-wide text-amber-700">Sources</p>
          <ul className="space-y-1">
            {(draft.sources || []).map((src, i) => {
              const url = (src.url || "").trim();
              const isHttp = /^https?:\/\//i.test(url);
              return (
              <li key={`${url}-${i}`} className="text-xs text-slate-700 break-all">
                {isHttp ? (
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-amber-800 underline underline-offset-2 hover:text-amber-950"
                  >
                    {src.title || url}
                  </a>
                ) : (
                  <span>{src.title || url || "—"} (no openable link)</span>
                )}
              </li>
              );
            })}
          </ul>
        </div>
      )}

      {(draft.missing_critical?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-100/60 p-3 text-xs text-amber-950">
          <p className="font-bold uppercase text-[9px] mb-1">Quality notes</p>
          <ul className="list-disc pl-4 space-y-0.5">
            {(draft.missing_critical || []).map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
        <div className="bg-white/80 rounded-lg border border-amber-100 p-3">
          <p className="text-amber-600 font-bold uppercase text-[9px]">Purpose</p>
          <p className="text-slate-700 mt-1">{draft.purpose || "—"}</p>
        </div>
        <div className="bg-white/80 rounded-lg border border-amber-100 p-3">
          <p className="text-amber-600 font-bold uppercase text-[9px]">Platform</p>
          <p className="text-slate-700 mt-1 capitalize">
            {draft.platform === "twitter" || draft.platform === "x"
              ? "X (Twitter)"
              : draft.platform || "—"}
          </p>
        </div>
        <div className="bg-white/80 rounded-lg border border-amber-100 p-3">
          <p className="text-amber-600 font-bold uppercase text-[9px]">Audience</p>
          <p className="text-slate-700 mt-1">{draft.audience || "—"}</p>
        </div>
        <div className="bg-white/80 rounded-lg border border-amber-100 p-3">
          <p className="text-amber-600 font-bold uppercase text-[9px]">Intent / Tone</p>
          <p className="text-slate-700 mt-1">
            {draft.intent || "—"} · {draft.tone || "—"}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field
          label="Hook"
          value={draft.hook || ""}
          onChange={(v) => setDraft((d) => ({ ...d, hook: v }))}
          rows={2}
        />
        <Field
          label="Storyline (one beat per line)"
          value={(draft.story_flow || []).join("\n")}
          onChange={(v) =>
            setDraft((d) => ({
              ...d,
              story_flow: v
                .split("\n")
                .map((line) => line.trim())
                .filter(Boolean),
            }))
          }
          rows={4}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Field
          label="Headline (heading)"
          value={draft.headline || ""}
          onChange={(v) => setDraft((d) => ({ ...d, headline: v }))}
          rows={2}
        />
        <Field
          label="Supporting line (subheading)"
          value={draft.supporting_line || ""}
          onChange={(v) => setDraft((d) => ({ ...d, supporting_line: v }))}
          rows={2}
        />
        <Field
          label="Body"
          value={draft.body || ""}
          onChange={(v) => setDraft((d) => ({ ...d, body: v }))}
          rows={4}
        />
        <Field
          label="CTA"
          value={draft.cta || ""}
          onChange={(v) => setDraft((d) => ({ ...d, cta: v }))}
          rows={2}
        />
      </div>

      {fmt === "carousel" && (draft.slides?.length ?? 0) > 0 && (
        <div className="space-y-3">
          <p className="text-[10px] font-bold uppercase text-amber-700">Carousel slides</p>
          {(draft.slides || []).map((slide, idx) => (
            <div key={slide.slide_number} className="bg-white rounded-xl border border-amber-100 p-4 space-y-2">
              <p className="text-xs font-semibold text-amber-900">
                Slide {slide.slide_number} · {slide.role}
              </p>
              <Field
                label="Headline"
                value={slide.headline || ""}
                onChange={(v) =>
                  setDraft((d) => {
                    const slides = [...(d.slides || [])];
                    slides[idx] = { ...slides[idx], headline: v };
                    return { ...d, slides };
                  })
                }
              />
              <Field
                label="Body"
                value={slide.body || ""}
                onChange={(v) =>
                  setDraft((d) => {
                    const slides = [...(d.slides || [])];
                    slides[idx] = { ...slides[idx], body: v };
                    return { ...d, slides };
                  })
                }
              />
              <Field
                label="CTA"
                value={slide.cta || ""}
                onChange={(v) =>
                  setDraft((d) => {
                    const slides = [...(d.slides || [])];
                    slides[idx] = { ...slides[idx], cta: v };
                    return { ...d, slides };
                  })
                }
                rows={1}
              />
            </div>
          ))}
        </div>
      )}

      {(fmt === "infographic" ||
        fmt === "static" ||
        draft.layout_type === "static_hub_facts" ||
        draft.layout_type === "static_ranking") &&
        (draft.sections?.length ?? 0) > 0 && (
        <div className="space-y-3">
          {fmt === "infographic" && (
            <Field
              label="Infographic title"
              value={draft.title || draft.headline || ""}
              onChange={(v) => setDraft((d) => ({ ...d, title: v, headline: v }))}
            />
          )}
          {(draft.sections || []).map((sec, idx) => (
            <div key={`${sec.section_label}-${idx}`} className="bg-white rounded-xl border border-amber-100 p-4 space-y-2">
              <Field
                label={`Section ${idx + 1} label`}
                value={sec.section_label || ""}
                onChange={(v) =>
                  setDraft((d) => {
                    const sections = [...(d.sections || [])];
                    sections[idx] = { ...sections[idx], section_label: v };
                    return { ...d, sections };
                  })
                }
                rows={1}
              />
              <Field
                label="Stat"
                value={sec.stat || ""}
                onChange={(v) =>
                  setDraft((d) => {
                    const sections = [...(d.sections || [])];
                    sections[idx] = { ...sections[idx], stat: v };
                    return { ...d, sections };
                  })
                }
                rows={1}
              />
              <Field
                label="Includes / facts (one per line)"
                value={(sec.includes || []).join("\n")}
                onChange={(v) =>
                  setDraft((d) => {
                    const sections = [...(d.sections || [])];
                    sections[idx] = {
                      ...sections[idx],
                      includes: v
                        .split("\n")
                        .map((line) => line.trim())
                        .filter(Boolean),
                    };
                    return { ...d, sections };
                  })
                }
              />
              <Field
                label="Body"
                value={sec.body || ""}
                onChange={(v) =>
                  setDraft((d) => {
                    const sections = [...(d.sections || [])];
                    sections[idx] = { ...sections[idx], body: v };
                    return { ...d, sections };
                  })
                }
              />
            </div>
          ))}
        </div>
      )}

      {fmt === "infographic" && (
        <div className="space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field
              label="Problem"
              value={draft.problem_statement || ""}
              onChange={(v) => setDraft((d) => ({ ...d, problem_statement: v }))}
            />
            <Field
              label="Solution"
              value={draft.solution_statement || ""}
              onChange={(v) => setDraft((d) => ({ ...d, solution_statement: v }))}
            />
          </div>
          <Field
            label="Customer quote"
            value={draft.customer_quote || ""}
            onChange={(v) => setDraft((d) => ({ ...d, customer_quote: v }))}
          />
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-3 pt-2">
        <Button
          onClick={() => onApprove(draft)}
          disabled={isApproving || blockApprove}
          className="flex-1 bg-amber-700 hover:bg-amber-800 text-white gap-2 h-11"
        >
          {isApproving ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
          Approve &amp; Generate Image
        </Button>
        <Button
          variant="outline"
          onClick={onCancel}
          disabled={isApproving}
          className="gap-2 h-11 border-amber-200 text-amber-900"
        >
          <XCircle className="h-4 w-4" />
          Cancel
        </Button>
      </div>
      {blockApprove ? (
        <p className="text-xs font-medium text-amber-900">{blockReason}</p>
      ) : null}
    </SurfaceCard>
  );
}
