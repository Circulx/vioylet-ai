"use client";

import { useState } from "react";
import { usePipeline } from "@/hooks/usePipeline";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Loader2,
  Send,
  Brain,
  Target,
  Lightbulb,
  ShieldCheck,
  BarChart3,
  Clock,
  Coins,
  Sparkles,
  LayoutGrid,
  CheckCircle2,
  XCircle,
  PenLine,
  Eye,
  Layers,
  Image as ImageIcon,
  Hash,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { SurfaceCard } from "@/components/common/DesignPrimitives";
import type { BrandTabProps } from "@/types/brand-space.types";
import { cn } from "@/lib/utils";
import { apiOrigin } from "@/lib/env";

function GeneratedImageCarousel({ imageUrls }: { imageUrls: string[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const validUrls = imageUrls.filter(Boolean);
  const clampedIndex = Math.min(activeIndex, Math.max(validUrls.length - 1, 0));

  if (validUrls.length === 0) return null;

  const goPrev = () => setActiveIndex((i) => (i - 1 + validUrls.length) % validUrls.length);
  const goNext = () => setActiveIndex((i) => (i + 1) % validUrls.length);

  return (
    <div className="space-y-2">
      <div className="relative rounded-xl overflow-hidden border border-indigo-100 bg-white">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${apiOrigin}${validUrls[clampedIndex]}`}
          alt={`Generated visual ${clampedIndex + 1} of ${validUrls.length}`}
          className="w-full h-auto"
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = "none";
          }}
        />
        {validUrls.length > 1 && (
          <>
            <button
              type="button"
              onClick={goPrev}
              aria-label="Previous slide"
              className="absolute left-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white text-indigo-700 rounded-full p-1.5 shadow border border-indigo-100"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={goNext}
              aria-label="Next slide"
              className="absolute right-2 top-1/2 -translate-y-1/2 bg-white/90 hover:bg-white text-indigo-700 rounded-full p-1.5 shadow border border-indigo-100"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5">
              {validUrls.map((_, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setActiveIndex(idx)}
                  aria-label={`Go to slide ${idx + 1}`}
                  className={cn(
                    "h-1.5 rounded-full transition-all",
                    idx === clampedIndex ? "w-5 bg-indigo-600" : "w-1.5 bg-indigo-200"
                  )}
                />
              ))}
            </div>
          </>
        )}
      </div>
      {validUrls.length > 1 && (
        <p className="text-slate-400 text-[9px] text-center">
          Slide {clampedIndex + 1} of {validUrls.length}
        </p>
      )}
      <p className="text-slate-400 text-[9px] break-all">URL: {apiOrigin}{validUrls[clampedIndex]}</p>
    </div>
  );
}

export default function IntelligencePipeline({ brandId }: BrandTabProps) {
  const [prompt, setPrompt] = useState("Create a LinkedIn post about why bonds are useful for predictable income.");
  const [platform, setPlatform] = useState<"linkedin" | "instagram" | "x">("linkedin");
  const [format, setFormat] = useState<"static" | "carousel" | "infographic">("static");
  
  const { runPipeline, isLoading, data } = usePipeline();

  const handleRun = () => {
    if (!prompt.trim()) return;
    runPipeline.mutate({
      brand_id: brandId,
      user_prompt: prompt,
      platform,
      format
    });
  };

  return (
    <div className="space-y-8 pb-20">
      <div className="space-y-4">
        <h2 className="text-xl font-semibold text-slate-900">Violyt Intelligence Pipeline (Milestone 6)</h2>
        <p className="text-sm text-slate-500">
          Run the 10-layer LangGraph intelligence pipeline. Layers 1-4 handle brand retrieval, intelligence,
          brief interpretation, and strategic reasoning. Layer 5 generates creative concepts (Claude) and
          Layer 6 builds a format-native content plan (GPT-4o) in parallel. Layer 7 generates brand-aligned copy
          (Claude), Layer 8 produces visual reasoning + DALL-E 3 image generation (GPT-4o), and Layer 9 maps
          the scene graph layout (GPT-4o).
        </p>
      </div>

      <SurfaceCard className="p-6 space-y-6 border-primary/20 bg-primary/5">
        <div className="space-y-4">
          <label className="text-sm font-semibold text-slate-700">Campaign Prompt</label>
          <Textarea 
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="What should we create?"
            className="min-h-[100px] bg-white border-slate-200"
          />
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-700">Platform</label>
            <div className="flex gap-2">
              {(["linkedin", "instagram", "x"] as const).map((p) => (
                <Button
                  key={p}
                  variant={platform === p ? "default" : "outline"}
                  onClick={() => setPlatform(p)}
                  className="capitalize"
                  size="sm"
                >
                  {p}
                </Button>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-700">Format</label>
            <div className="flex gap-2">
              {(["static", "carousel", "infographic"] as const).map((f) => (
                <Button
                  key={f}
                  variant={format === f ? "default" : "outline"}
                  onClick={() => setFormat(f)}
                  className="capitalize"
                  size="sm"
                >
                  {f}
                </Button>
              ))}
            </div>
          </div>
        </div>

        <Button 
          onClick={handleRun} 
          disabled={isLoading || !prompt.trim()} 
          className="w-full bg-primary hover:bg-primary/90 text-white gap-2 h-12"
        >
          {isLoading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
          Run Pipeline
        </Button>
      </SurfaceCard>

      {data && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
          {data.status === "failed" && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
              <XCircle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-bold text-red-800 text-sm">Pipeline Failed</p>
                <p className="text-red-600 text-xs mt-1">{data.error || "Unknown error"}</p>
              </div>
            </div>
          )}
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <Brain className="h-6 w-6 text-primary" />
              Pipeline Results
              <span className={cn(
                "ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase",
                data.status === "complete" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
              )}>
                {data.status}
              </span>
            </h3>
            <div className="flex gap-4 text-xs font-medium text-slate-500">
              <span className="flex items-center gap-1.5 bg-slate-100 px-2 py-1 rounded">
                <Clock className="h-3.5 w-3.5" />
                {Object.values(data.layer_latencies || {}).reduce((a, b) => a + b, 0)}ms total
              </span>
              <span className="flex items-center gap-1.5 bg-slate-100 px-2 py-1 rounded">
                <Coins className="h-3.5 w-3.5" />
                {Object.values(data.token_usage || {}).reduce((a, b) => a + b.input_tokens + b.output_tokens, 0)} tokens
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Layer 2: Brand Intelligence */}
            <SurfaceCard className="p-5 border-emerald-100 bg-emerald-50/30">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-emerald-100 p-2 rounded-lg">
                  <ShieldCheck className="h-5 w-5 text-emerald-600" />
                </div>
                <div>
                  <h4 className="font-bold text-emerald-900 text-sm">L2: Brand Intelligence</h4>
                  <p className="text-[10px] text-emerald-600 font-medium">Model: Claude Sonnet 4.6</p>
                </div>
              </div>
              <div className="space-y-3 text-xs">
                <div>
                  <span className="font-bold text-emerald-800">Value Prop:</span>
                  <p className="text-slate-600 mt-0.5">{data.brand_intelligence?.brand_core.value_proposition}</p>
                </div>
                <div>
                  <span className="font-bold text-emerald-800">Tone:</span>
                  <p className="text-slate-600 mt-0.5">{data.brand_intelligence?.communication_behavior.tone_spectrum}</p>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {data.brand_intelligence?.brand_core.stands_for.map(s => (
                    <span key={s} className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full text-[10px]">
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </SurfaceCard>

            {/* Layer 3: Brief Interpreter */}
            <SurfaceCard className="p-5 border-blue-100 bg-blue-50/30">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-blue-100 p-2 rounded-lg">
                  <Target className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <h4 className="font-bold text-blue-900 text-sm">L3: Brief Interpreter</h4>
                  <p className="text-[10px] text-blue-600 font-medium">Model: GPT-4o</p>
                </div>
              </div>
              <div className="space-y-3 text-xs">
                <div>
                  <span className="font-bold text-blue-800">Objective:</span>
                  <p className="text-slate-600 mt-0.5">{data.campaign_brief?.campaign_objective}</p>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bg-white p-2 rounded border border-blue-50">
                    <p className="text-blue-500 font-bold uppercase text-[9px]">Funnel Stage</p>
                    <p className="text-slate-700 capitalize">{data.campaign_brief?.funnel_stage}</p>
                  </div>
                  <div className="bg-white p-2 rounded border border-blue-50">
                    <p className="text-blue-500 font-bold uppercase text-[9px]">Content Role</p>
                    <p className="text-slate-700 capitalize">{data.campaign_brief?.content_role}</p>
                  </div>
                </div>
              </div>
            </SurfaceCard>

            {/* Layer 4: Strategic Reasoning */}
            <SurfaceCard className="col-span-1 md:col-span-2 p-5 border-purple-100 bg-purple-50/30">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-purple-100 p-2 rounded-lg">
                  <Lightbulb className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <h4 className="font-bold text-purple-900 text-sm">L4: Strategic Reasoning</h4>
                  <p className="text-[10px] text-purple-600 font-medium">Model: Claude Sonnet 4.6</p>
                </div>
              </div>
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <span className="font-bold text-purple-800 text-[11px]">Brand Truth:</span>
                    <p className="text-slate-700 leading-relaxed bg-white/50 p-3 rounded-xl border border-purple-50 italic">
                      "{data.strategic_reasoning?.brand_truth}"
                    </p>
                  </div>
                  <div className="space-y-2">
                    <span className="font-bold text-purple-800 text-[11px]">Recommended Approach:</span>
                    <p className="text-slate-700 leading-relaxed bg-white/50 p-3 rounded-xl border border-purple-50">
                      {data.strategic_reasoning?.recommended_approach}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="font-bold text-purple-800 text-[11px]">Rejected Approaches:</span>
                  <div className="space-y-2">
                    {data.strategic_reasoning?.rejected_approaches.map((ra, idx) => (
                      <div key={idx} className="bg-white/40 p-2.5 rounded-lg border border-purple-50 flex items-start gap-3">
                        <div className="bg-red-50 text-red-500 px-1.5 py-0.5 rounded text-[9px] font-bold mt-0.5">REJECTED</div>
                        <div>
                          <p className="font-semibold text-slate-700">{ra.approach_name}</p>
                          <p className="text-slate-500 mt-0.5">{ra.rejection_reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </SurfaceCard>

            {/* Layer 5: Creative Concepts */}
            <SurfaceCard className="col-span-1 md:col-span-2 p-5 border-amber-100 bg-amber-50/30">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-amber-100 p-2 rounded-lg">
                  <Sparkles className="h-5 w-5 text-amber-600" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-amber-900 text-sm">L5: Creative Concepts</h4>
                    <span className="bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full text-[9px] font-bold">
                      Diversity: {Math.round((data.creative_concepts?.diversity_score || 0) * 100)}%
                    </span>
                  </div>
                  <p className="text-[10px] text-amber-600 font-medium">Model: Claude Sonnet 4.6 · {data.creative_concepts?.all_concepts.length} concepts generated</p>
                </div>
              </div>
              <div className="space-y-4 text-xs">
                {/* Recommended concept highlighted */}
                <div className="bg-amber-100/60 border border-amber-200 p-3 rounded-xl">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="h-4 w-4 text-amber-600" />
                    <span className="font-bold text-amber-900 text-[11px]">RECOMMENDED: {data.creative_concepts?.recommended_concept.concept_name}</span>
                  </div>
                  <p className="text-slate-700 leading-relaxed mb-2">{data.creative_concepts?.recommended_concept.core_idea}</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                    <div><span className="font-bold text-amber-800">Hook:</span> <span className="text-slate-600 italic">"{data.creative_concepts?.recommended_concept.hook}"</span></div>
                    <div><span className="font-bold text-amber-800">Visual:</span> <span className="text-slate-600">{data.creative_concepts?.recommended_concept.visual_angle}</span></div>
                  </div>
                  <p className="mt-2 text-slate-500"><span className="font-bold text-amber-800">Selection Reason:</span> {data.creative_concepts?.selection_reason}</p>
                </div>

                {/* All concepts grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {data.creative_concepts?.all_concepts.map((concept) => (
                    <div
                      key={concept.concept_id}
                      className={cn(
                        "p-3 rounded-lg border space-y-2",
                        concept.concept_id === data.creative_concepts?.recommended_concept.concept_id
                          ? "bg-amber-50 border-amber-200"
                          : "bg-white border-slate-100"
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-800 text-[11px]">{concept.concept_name}</span>
                        <span className={cn(
                          "px-1.5 py-0.5 rounded text-[8px] font-bold uppercase",
                          concept.risk_level === "low" ? "bg-emerald-50 text-emerald-600" :
                          concept.risk_level === "medium" ? "bg-amber-50 text-amber-600" :
                          "bg-red-50 text-red-600"
                        )}>
                          {concept.risk_level}
                        </span>
                      </div>
                      <p className="text-slate-500 text-[10px] leading-relaxed">{concept.core_idea}</p>
                      <p className="text-slate-400 text-[9px]"><span className="font-bold">Narrative:</span> {concept.narrative_angle}</p>
                      <p className="text-slate-400 text-[9px]"><span className="font-bold">Brand Fit:</span> {concept.brand_fit_reason}</p>
                    </div>
                  ))}
                </div>

                {/* Rejected concepts */}
                {data.creative_concepts?.rejected_concepts && data.creative_concepts.rejected_concepts.length > 0 && (
                  <div className="space-y-2">
                    <span className="font-bold text-amber-800 text-[11px]">Rejected Concepts:</span>
                    {data.creative_concepts.rejected_concepts.map((rc, idx) => (
                      <div key={idx} className="bg-white/40 p-2.5 rounded-lg border border-amber-50 flex items-start gap-3">
                        <XCircle className="h-3.5 w-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="font-semibold text-slate-700 text-[10px]">{rc.concept_id}</p>
                          <p className="text-slate-500 text-[10px] mt-0.5">{rc.rejection_reason}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </SurfaceCard>

            {/* Layer 6: Format Intelligence */}
            <SurfaceCard className="col-span-1 md:col-span-2 p-5 border-cyan-100 bg-cyan-50/30">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-cyan-100 p-2 rounded-lg">
                  <LayoutGrid className="h-5 w-5 text-cyan-600" />
                </div>
                <div>
                  <h4 className="font-bold text-cyan-900 text-sm">L6: Format Intelligence</h4>
                  <p className="text-[10px] text-cyan-600 font-medium">Model: GPT-4o · {data.format_plan?.slide_plan.length} slides planned</p>
                </div>
              </div>
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="bg-white p-2.5 rounded-lg border border-cyan-50">
                    <p className="text-cyan-500 font-bold uppercase text-[8px]">Strategy</p>
                    <p className="text-slate-700 text-[10px] mt-0.5">{data.format_plan?.format_strategy}</p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-cyan-50">
                    <p className="text-cyan-500 font-bold uppercase text-[8px]">Layout</p>
                    <p className="text-slate-700 text-[10px] mt-0.5">{data.format_plan?.layout_archetype}</p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-cyan-50">
                    <p className="text-cyan-500 font-bold uppercase text-[8px]">Copy Density</p>
                    <p className="text-slate-700 capitalize text-[10px] mt-0.5">{data.format_plan?.copy_density}</p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-cyan-50">
                    <p className="text-cyan-500 font-bold uppercase text-[8px]">Visual Density</p>
                    <p className="text-slate-700 capitalize text-[10px] mt-0.5">{data.format_plan?.visual_density}</p>
                  </div>
                </div>

                <div>
                  <span className="font-bold text-cyan-800 text-[11px]">Content Structure:</span>
                  <p className="text-slate-600 mt-0.5">{data.format_plan?.content_structure}</p>
                </div>

                {/* Slide plan */}
                <div className="space-y-2">
                  <span className="font-bold text-cyan-800 text-[11px]">Slide Plan:</span>
                  <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2 thin-scrollbar">
                    {data.format_plan?.slide_plan.map((slide) => (
                      <div key={slide.slide_number} className="bg-white p-3 rounded-lg border border-cyan-50 flex items-start gap-3">
                        <div className="bg-cyan-100 text-cyan-700 w-7 h-7 rounded-full flex items-center justify-center font-bold text-[10px] flex-shrink-0">
                          {slide.slide_number}
                        </div>
                        <div className="flex-1 space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-800 text-[10px] uppercase">{slide.role}</span>
                          </div>
                          <p className="text-slate-600 text-[10px]"><span className="font-bold">Focus:</span> {slide.focus}</p>
                          <p className="text-slate-500 text-[10px]"><span className="font-bold">Copy:</span> {slide.copy_intent}</p>
                          <p className="text-slate-500 text-[10px]"><span className="font-bold">Visual:</span> {slide.visual_intent}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {data.format_plan?.notes && (
                  <p className="text-slate-400 text-[10px] italic">{data.format_plan.notes}</p>
                )}
              </div>
            </SurfaceCard>

            {/* Layer 7: Copy Engine */}
            <SurfaceCard className="col-span-1 md:col-span-2 p-5 border-rose-100 bg-rose-50/30">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-rose-100 p-2 rounded-lg">
                  <PenLine className="h-5 w-5 text-rose-600" />
                </div>
                <div>
                  <h4 className="font-bold text-rose-900 text-sm">L7: Copy Engine</h4>
                  <p className="text-[10px] text-rose-600 font-medium">Model: Claude Sonnet 4.6 · {data.copy?.slide_copy.length || 0} slides written</p>
                </div>
              </div>
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <span className="font-bold text-rose-800 text-[11px]">Headline:</span>
                    <p className="text-slate-700 leading-relaxed bg-white/50 p-3 rounded-xl border border-rose-50 font-semibold">
                      {data.copy?.headline}
                    </p>
                  </div>
                  <div className="space-y-2">
                    <span className="font-bold text-rose-800 text-[11px]">CTA:</span>
                    <p className="text-slate-700 leading-relaxed bg-white/50 p-3 rounded-xl border border-rose-50">
                      {data.copy?.cta}
                    </p>
                  </div>
                </div>
                {data.copy?.supporting_line && (
                  <div>
                    <span className="font-bold text-rose-800 text-[11px]">Supporting Line:</span>
                    <p className="text-slate-600 mt-0.5">{data.copy.supporting_line}</p>
                  </div>
                )}
                <div>
                  <span className="font-bold text-rose-800 text-[11px]">Body:</span>
                  <p className="text-slate-600 mt-0.5 leading-relaxed">{data.copy?.body}</p>
                </div>
                {data.copy?.hashtags && data.copy.hashtags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    <Hash className="h-3.5 w-3.5 text-rose-400" />
                    {data.copy.hashtags.map((tag, idx) => (
                      <span key={idx} className="bg-rose-100 text-rose-700 px-2 py-0.5 rounded-full text-[10px]">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
                {data.copy?.slide_copy && data.copy.slide_copy.length > 0 && (
                  <div className="space-y-2">
                    <span className="font-bold text-rose-800 text-[11px]">Slide Copy:</span>
                    <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2 thin-scrollbar">
                      {data.copy.slide_copy.map((slide) => (
                        <div key={slide.slide_number} className="bg-white p-3 rounded-lg border border-rose-50 flex items-start gap-3">
                          <div className="bg-rose-100 text-rose-700 w-7 h-7 rounded-full flex items-center justify-center font-bold text-[10px] flex-shrink-0">
                            {slide.slide_number}
                          </div>
                          <div className="flex-1 space-y-1">
                            <span className="font-bold text-slate-800 text-[10px]">{slide.headline}</span>
                            {slide.supporting_line && <p className="text-slate-500 text-[10px] italic">{slide.supporting_line}</p>}
                            <p className="text-slate-600 text-[10px]">{slide.body}</p>
                            {slide.cta && <p className="text-rose-600 text-[10px] font-bold">→ {slide.cta}</p>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                {data.copy?.claim_safety_notes && data.copy.claim_safety_notes.length > 0 && (
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold text-amber-800 text-[10px]">Claim Safety Notes:</p>
                      <ul className="text-amber-700 text-[10px] mt-1 space-y-0.5">
                        {data.copy.claim_safety_notes.map((note, idx) => (
                          <li key={idx}>• {note}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            </SurfaceCard>

            {/* Layer 8: Visual Reasoning */}
            <SurfaceCard className="col-span-1 md:col-span-2 p-5 border-indigo-100 bg-indigo-50/30">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-indigo-100 p-2 rounded-lg">
                  <Eye className="h-5 w-5 text-indigo-600" />
                </div>
                <div>
                  <h4 className="font-bold text-indigo-900 text-sm">L8: Visual Reasoning</h4>
                  <p className="text-[10px] text-indigo-600 font-medium">Model: GPT-4o · DALL-E 3 Image Generation</p>
                </div>
              </div>
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div className="bg-white p-2.5 rounded-lg border border-indigo-50">
                    <p className="text-indigo-500 font-bold uppercase text-[8px]">Visual System</p>
                    <p className="text-slate-700 text-[10px] mt-0.5 capitalize">{data.visual_reasoning?.dominant_visual_system?.replace(/_/g, " ")}</p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-indigo-50">
                    <p className="text-indigo-500 font-bold uppercase text-[8px]">Focal Point</p>
                    <p className="text-slate-700 text-[10px] mt-0.5">{data.visual_reasoning?.focal_point}</p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-indigo-50">
                    <p className="text-indigo-500 font-bold uppercase text-[8px]">Logo Zone</p>
                    <p className="text-slate-700 text-[10px] mt-0.5">{data.visual_reasoning?.logo_zone_instruction}</p>
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <span className="font-bold text-indigo-800 text-[11px]">Visual Style:</span>
                    <p className="text-slate-600 mt-0.5">{data.visual_reasoning?.visual_style}</p>
                  </div>
                  <div>
                    <span className="font-bold text-indigo-800 text-[11px]">Composition:</span>
                    <p className="text-slate-600 mt-0.5">{data.visual_reasoning?.composition_logic}</p>
                  </div>
                </div>
                <div>
                  <span className="font-bold text-indigo-800 text-[11px]">Negative Space Plan:</span>
                  <p className="text-slate-600 mt-0.5">{data.visual_reasoning?.negative_space_plan}</p>
                </div>
                <div>
                  <span className="font-bold text-indigo-800 text-[11px]">Color Behavior:</span>
                  <p className="text-slate-600 mt-0.5">{data.visual_reasoning?.color_behavior}</p>
                </div>
                <div className="bg-indigo-50/50 p-3 rounded-xl border border-indigo-100">
                  <span className="font-bold text-indigo-800 text-[11px]">DALL-E 3 Prompt:</span>
                  <p className="text-slate-600 mt-0.5 text-[10px] italic leading-relaxed">{data.visual_reasoning?.image_prompt_direction}</p>
                </div>
                {/* Infographic: show only the final rendered image with text, bullets, and icons */}
                {data.format === "infographic" && data.final_output?.asset_url && (
                  <div className="space-y-2">
                    <span className="font-bold text-emerald-800 text-[11px] flex items-center gap-1.5">
                      <ImageIcon className="h-3.5 w-3.5" />
                      Infographic:
                    </span>
                    <GeneratedImageCarousel imageUrls={[data.final_output.asset_url]} />
                  </div>
                )}

                {data.format !== "infographic" && (data.visual_reasoning?.generated_image_urls?.length || data.visual_reasoning?.generated_image_url) && (
                  <div className="space-y-2">
                    <span className={cn(
                      "font-bold text-[11px] flex items-center gap-1.5",
                      "text-indigo-800"
                    )}>
                      <ImageIcon className="h-3.5 w-3.5" />
                      {(data.visual_reasoning?.generated_image_urls?.length || 0) > 1
                        ? `Generated Slides (${data.visual_reasoning?.generated_image_urls?.length}):`
                        : "Generated Image:"}
                    </span>
                    <GeneratedImageCarousel
                      imageUrls={
                        data.visual_reasoning?.generated_image_urls?.length
                          ? data.visual_reasoning.generated_image_urls
                          : [data.visual_reasoning?.generated_image_url || ""]
                      }
                    />
                  </div>
                )}
              </div>
            </SurfaceCard>

            {/* Layer 9: Scene Graph */}
            <SurfaceCard className="col-span-1 md:col-span-2 p-5 border-teal-100 bg-teal-50/30">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-teal-100 p-2 rounded-lg">
                  <Layers className="h-5 w-5 text-teal-600" />
                </div>
                <div>
                  <h4 className="font-bold text-teal-900 text-sm">L9: Scene Graph</h4>
                  <p className="text-[10px] text-teal-600 font-medium">Model: GPT-4o · {data.scene_graph?.elements.length || 0} elements · {data.scene_graph?.canvas_width}x{data.scene_graph?.canvas_height}</p>
                </div>
              </div>
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-white p-2.5 rounded-lg border border-teal-50">
                    <p className="text-teal-500 font-bold uppercase text-[8px]">Platform</p>
                    <p className="text-slate-700 text-[10px] mt-0.5 capitalize">{data.scene_graph?.platform}</p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-teal-50">
                    <p className="text-teal-500 font-bold uppercase text-[8px]">Ratio</p>
                    <p className="text-slate-700 text-[10px] mt-0.5">{data.scene_graph?.platform_ratio}</p>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-teal-50">
                    <p className="text-teal-500 font-bold uppercase text-[8px]">Layers</p>
                    <p className="text-slate-700 text-[10px] mt-0.5">{data.scene_graph?.layers.join(", ")}</p>
                  </div>
                </div>
                {data.scene_graph?.elements && data.scene_graph.elements.length > 0 && (
                  <div className="space-y-2">
                    <span className="font-bold text-teal-800 text-[11px]">Elements:</span>
                    <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 thin-scrollbar">
                      {data.scene_graph.elements.map((el) => (
                        <div key={el.element_id} className="bg-white p-3 rounded-lg border border-teal-50 flex items-start gap-3">
                          <div className={cn(
                            "px-2 py-0.5 rounded text-[8px] font-bold uppercase flex-shrink-0",
                            el.element_type === "background" ? "bg-slate-100 text-slate-600" :
                            el.element_type === "visual" ? "bg-indigo-100 text-indigo-600" :
                            el.element_type === "copy" ? "bg-rose-100 text-rose-600" :
                            el.element_type === "logo" ? "bg-amber-100 text-amber-600" :
                            el.element_type === "cta" ? "bg-emerald-100 text-emerald-600" :
                            "bg-teal-100 text-teal-600"
                          )}>
                            {el.element_type}
                          </div>
                          <div className="flex-1 space-y-1">
                            <p className="font-bold text-slate-800 text-[10px]">{el.element_id}</p>
                            <p className="text-slate-600 text-[10px]">{el.content}</p>
                            <p className="text-slate-400 text-[9px]">
                              pos: ({el.position.x}, {el.position.y}) · size: {el.position.width}x{el.position.height}
                            </p>
                            {el.asset_url && (
                              <p className="text-indigo-500 text-[9px] break-all">asset: {el.asset_url}</p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </SurfaceCard>

            {/* Layer 1: Retrieval Logs */}
            <SurfaceCard className="col-span-1 md:col-span-2 p-5 border-slate-200 bg-slate-50/50">
              <div className="flex items-center gap-2 mb-4">
                <div className="bg-slate-200 p-2 rounded-lg">
                  <BarChart3 className="h-5 w-5 text-slate-600" />
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">L1: Brand Retrieval Summary</h4>
                  <p className="text-[10px] text-slate-500 font-medium">Provider: Pinecone + OpenAI Embedding</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="bg-white p-3 rounded-xl border border-slate-200 text-center">
                  <p className="text-[9px] font-bold text-slate-400 uppercase">Chunks</p>
                  <p className="text-lg font-bold text-slate-700">{data.brand_context?.total_chunks_retrieved}</p>
                </div>
                <div className="bg-white p-3 rounded-xl border border-slate-200 text-center">
                  <p className="text-[9px] font-bold text-slate-400 uppercase">Confidence</p>
                  <p className="text-lg font-bold text-slate-700">{Math.round((data.brand_context?.retrieval_confidence || 0) * 100)}%</p>
                </div>
                <div className="bg-white p-3 rounded-xl border border-slate-200 text-center">
                  <p className="text-[9px] font-bold text-slate-400 uppercase">Isolation</p>
                  <p className={cn(
                    "text-lg font-bold uppercase",
                    data.brand_context?.brand_isolation_status === "pass" ? "text-emerald-600" : "text-amber-600"
                  )}>
                    {data.brand_context?.brand_isolation_status}
                  </p>
                </div>
              </div>
              <div className="space-y-2 max-h-[200px] overflow-y-auto pr-2 thin-scrollbar text-xs">
                {data.brand_context?.high_relevance_context.map((chunk, idx) => (
                  <div key={idx} className="bg-white p-3 rounded-lg border border-slate-100 space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-700">{chunk.source}</span>
                      <span className="bg-emerald-50 text-emerald-600 px-1.5 py-0.5 rounded text-[9px] font-bold">HIGH</span>
                    </div>
                    <p className="text-slate-500 italic">"{chunk.content_summary}"</p>
                  </div>
                ))}
              </div>
            </SurfaceCard>
          </div>
        </div>
      )}
    </div>
  );
}
