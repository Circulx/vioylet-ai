"use client";

import { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Clock, Coins, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";

export type LayerTokenUsage = {
  input_tokens: number;
  output_tokens: number;
};

type Props = {
  layerLatencies?: Record<string, number>;
  tokenUsage?: Record<string, LayerTokenUsage>;
  imageCount?: number;
  className?: string;
};

const LAYER_LABELS: Record<string, string> = {
  l1_retrieval: "L1 Retrieval",
  l1_brand_retrieval: "L1 Brand Retrieve",
  l2_brand_intelligence: "L2 Brand Intelligence",
  l3_brief_interpreter: "L3 Understand (Brief)",
  l4_strategic_reasoning: "L4 Reason",
  l5_creative_concepts: "L5 Conceptualize",
  l5_concept_engine: "L5 Conceptualize",
  l6_format_plan: "L6 Plan Format",
  l6_format_engine: "L6 Plan Format",
  l6b_content_intelligence: "L6b Evidence→Insight",
  l7_copy_engine: "L7 Generate Copy",
  l7b_copy_validation: "L7b Hygiene",
  l7b_content_validator: "L7b Hygiene",
  l7c_content_prep: "L7c Blueprint Plan",
  l8_visual_reasoning: "L8 Generate Visual",
  l8_prompt_expander: "L8 Prompt Expander",
  l9_scene_graph: "L9 Scene Graph",
  l10_evaluation: "L10 Evaluate",
  repair: "Repair",
  renderer: "Renderer",
};

const LAYER_MODELS: Record<string, string> = {
  l1_retrieval: "Embeddings",
  l1_brand_retrieval: "Embeddings",
  l2_brand_intelligence: "Claude",
  l3_brief_interpreter: "GPT-4o mini",
  l4_strategic_reasoning: "Claude",
  l5_creative_concepts: "Claude",
  l5_concept_engine: "Claude",
  l6_format_plan: "GPT-4o mini",
  l6_format_engine: "GPT-4o mini",
  l6b_content_intelligence: "Claude + Research",
  l7_copy_engine: "Claude",
  l7b_copy_validation: "GPT-4o mini",
  l7b_content_validator: "GPT-4o mini",
  l7c_content_prep: "Claude",
  l8_visual_reasoning: "GPT-4o + DALL·E",
  l8_prompt_expander: "GPT-4o",
  l9_scene_graph: "GPT-4o mini",
  l10_evaluation: "Rules + Editorial QA",
  repair: "Router",
  renderer: "Pillow",
};

function formatMs(ms: number): string {
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`;
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms}ms`;
}

function layerLabel(key: string): string {
  return LAYER_LABELS[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function layerModel(key: string): string {
  return LAYER_MODELS[key] || "LLM";
}

export default function PromptRunAnalytics({
  layerLatencies,
  tokenUsage,
  imageCount = 0,
  className,
}: Props) {
  const [open, setOpen] = useState(false);

  const rows = useMemo(() => {
    const keys = new Set([
      ...Object.keys(layerLatencies || {}),
      ...Object.keys(tokenUsage || {}),
    ]);
    return Array.from(keys)
      .map((key) => {
        const usage = tokenUsage?.[key];
        const input = usage?.input_tokens || 0;
        const output = usage?.output_tokens || 0;
        return {
          key,
          label: layerLabel(key),
          model: layerModel(key),
          latency: layerLatencies?.[key] || 0,
          input,
          output,
          total: input + output,
        };
      })
      .filter((row) => row.latency > 0 || row.total > 0)
      .sort((a, b) => b.latency - a.latency);
  }, [layerLatencies, tokenUsage]);

  const totalMs = useMemo(
    () => Object.values(layerLatencies || {}).reduce((sum, value) => sum + value, 0),
    [layerLatencies],
  );
  const totalTokens = useMemo(
    () =>
      Object.values(tokenUsage || {}).reduce(
        (sum, usage) => sum + (usage.input_tokens || 0) + (usage.output_tokens || 0),
        0,
      ),
    [tokenUsage],
  );
  const totalInput = useMemo(
    () => Object.values(tokenUsage || {}).reduce((sum, usage) => sum + (usage.input_tokens || 0), 0),
    [tokenUsage],
  );
  const totalOutput = useMemo(
    () => Object.values(tokenUsage || {}).reduce((sum, usage) => sum + (usage.output_tokens || 0), 0),
    [tokenUsage],
  );

  if (!rows.length && !totalMs && !totalTokens) {
    return null;
  }

  return (
    <div className={cn("rounded-lg border border-[#E8EAF0] bg-white", className)}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
      >
        <div className="flex flex-wrap items-center gap-2 text-[11px] font-medium text-[#4A4F6B]">
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5">
            <Clock className="h-3 w-3" />
            {formatMs(totalMs)} total
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5">
            <Coins className="h-3 w-3" />
            {totalTokens.toLocaleString()} tokens
          </span>
          {imageCount > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5">
              <Cpu className="h-3 w-3" />
              {imageCount} image{imageCount === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>
        <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary">
          Run analytics
          {open ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
        </span>
      </button>

      {open ? (
        <div className="border-t border-[#EEF0F5] px-3 py-2">
          <div className="mb-2 grid grid-cols-3 gap-2 text-[10px] text-[#6A6E8B]">
            <div className="rounded bg-slate-50 px-2 py-1.5">
              <p className="font-semibold text-[#121212]">Input</p>
              <p>{totalInput.toLocaleString()}</p>
            </div>
            <div className="rounded bg-slate-50 px-2 py-1.5">
              <p className="font-semibold text-[#121212]">Output</p>
              <p>{totalOutput.toLocaleString()}</p>
            </div>
            <div className="rounded bg-slate-50 px-2 py-1.5">
              <p className="font-semibold text-[#121212]">Wall time</p>
              <p>{formatMs(totalMs)}</p>
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            <table className="w-full text-left text-[10px]">
              <thead>
                <tr className="text-[#6A6E8B]">
                  <th className="pb-1 font-medium">Layer</th>
                  <th className="pb-1 font-medium">Model</th>
                  <th className="pb-1 font-medium text-right">Time</th>
                  <th className="pb-1 font-medium text-right">Tokens</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.key} className="border-t border-[#F3F4F8] text-[#121212]">
                    <td className="py-1.5 pr-2 font-medium">{row.label}</td>
                    <td className="py-1.5 pr-2 text-[#6A6E8B]">{row.model}</td>
                    <td className="py-1.5 text-right tabular-nums">{row.latency ? formatMs(row.latency) : "—"}</td>
                    <td className="py-1.5 text-right tabular-nums">
                      {row.total ? row.total.toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}
