"use client";

import { CheckCircle2, Circle } from "lucide-react";
import type { BrandTabProps } from "@/types/brand-space.types";

type ReviewItem = {
    label: string;
    filled: boolean;
    detail?: string;
};

type ReviewSection = {
    title: string;
    layer: string;
    color: string;
    items: ReviewItem[];
};

function ReviewCard({ section }: { section: ReviewSection }) {
    const total = section.items.length;
    const completed = section.items.filter((i) => i.filled).length;
    const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

    return (
        <div className="rounded-xl border border-[#E3E6F2] bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-start justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">{section.layer}</p>
                    <h3 className="mt-0.5 text-base font-semibold text-slate-800">{section.title}</h3>
                </div>
                <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                        percent === 100
                            ? "bg-emerald-50 text-emerald-700"
                            : percent >= 50
                              ? "bg-amber-50 text-amber-700"
                              : "bg-slate-100 text-slate-500"
                    }`}
                >
                    {percent}%
                </span>
            </div>

            {/* Progress bar */}
            <div className="mb-4 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                    className={`h-full rounded-full transition-all ${
                        percent === 100 ? "bg-emerald-500" : percent >= 50 ? "bg-amber-400" : "bg-primary/50"
                    }`}
                    style={{ width: `${percent}%` }}
                />
            </div>

            <ul className="space-y-2">
                {section.items.map((item) => (
                    <li key={item.label} className="flex items-start gap-2.5 text-sm">
                        {item.filled ? (
                            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                        ) : (
                            <Circle className="mt-0.5 h-4 w-4 shrink-0 text-slate-300" />
                        )}
                        <span className={item.filled ? "text-slate-700" : "text-slate-400"}>{item.label}</span>
                        {item.detail && (
                            <span className="ml-auto max-w-[200px] truncate text-right text-xs text-slate-400">
                                {item.detail}
                            </span>
                        )}
                    </li>
                ))}
            </ul>
        </div>
    );
}

const BrandReview = ({ brandId, form }: BrandTabProps) => {
    const f = form;

    const sections: ReviewSection[] = [
        {
            title: "Brand Space Creation",
            layer: "Identity Layer",
            color: "primary",
            items: [
                { label: "Brand Name", filled: Boolean(f.core.name) },
                { label: "Tagline", filled: Boolean(f.core.tagline) },
                { label: "Brand Description", filled: Boolean(f.core.description) },
                { label: "Industry Category", filled: Boolean(f.core.industryCategory) },
                { label: "Key Differentiators", filled: Boolean(f.core.differentiators) },
                { label: "Brand Logo", filled: Boolean(f.core.logos.length) },
            ],
        },
        {
            title: "Brand Foundations",
            layer: "Strategic Layer",
            color: "amber",
            items: [
                { label: "Brand Mission", filled: Boolean(f.additional.brandMission) },
                { label: "Brand Vision", filled: Boolean(f.additional.brandVision) },
                { label: "Brand Promise", filled: Boolean(f.additional.brandPromise) },
                { label: "Market Positioning", filled: Boolean(f.additional.marketPositioning) },
                { label: "Business Problem / Opportunity", filled: Boolean(f.additional.businessProblemOrOpportunity) },
                { label: "Brand Archetype", filled: Boolean(f.additional.brandArchetype) },
            ],
        },
        {
            title: "Brand Voice & Emotion Mapping",
            layer: "Tone Layer",
            color: "purple",
            items: [
                { label: "Core Tone Attributes", filled: f.voiceTone.coreToneAttributes.length > 0 },
                { label: "Primary Emotion", filled: Boolean(f.voiceTone.primaryEmotion) },
                { label: "Secondary Emotion", filled: Boolean(f.voiceTone.secondaryEmotion) },
                { label: "Content Complexity", filled: Boolean(f.voiceTone.contentComplexity) },
                { label: "Sentence Length", filled: Boolean(f.voiceTone.sentenceLength) },
                { label: "Perspective", filled: Boolean(f.voiceTone.perspective) },
            ],
        },
        {
            title: "Audience Persona Mapping",
            layer: "Persona Intelligence Layer",
            color: "blue",
            items: [
                { label: "Audience Type", filled: f.targetAudience.selectedAudiences.length > 0 },
                { label: "Goals", filled: Boolean(f.targetAudience.goals) },
                { label: "Motivations", filled: Boolean(f.targetAudience.motivations) },
                { label: "Fears & Pain Points", filled: Boolean(f.targetAudience.fearsAndPainPoints) },
                { label: "Age Range", filled: Boolean(f.targetAudience.ageRange) },
                { label: "Location", filled: Boolean(f.targetAudience.location) },
            ],
        },
        {
            title: "Do's & Don'ts",
            layer: "Guardrail Layer",
            color: "red",
            items: [
                { label: "Do's", filled: Boolean(f.brandRules.whatToDo) },
                { label: "Don'ts", filled: Boolean(f.brandRules.whatNotToDo) },
                { label: "Positive Word Bank", filled: Boolean(f.brandRules.positiveWordBank) },
                { label: "Negative Word Bank", filled: Boolean(f.brandRules.negativeWordBank) },
                { label: "Restricted Topics", filled: Boolean(f.brandRules.restrictedTopics) },
            ],
        },
        {
            title: "Brand Knowledge Upload",
            layer: "Learning Layer",
            color: "green",
            items: [
                { label: "Templates uploaded", filled: f.brandKnowledge.templateFiles.length > 0, detail: f.brandKnowledge.templateFiles.length > 0 ? `${f.brandKnowledge.templateFiles.length} file(s)` : undefined },
                { label: "Other documents", filled: f.brandKnowledge.otherDocuments.length > 0, detail: f.brandKnowledge.otherDocuments.length > 0 ? `${f.brandKnowledge.otherDocuments.length} file(s)` : undefined },
            ],
        },
        {
            title: "Prompt Intelligence Setup",
            layer: "Instruction Layer",
            color: "indigo",
            items: [
                { label: "Preferred Platforms", filled: f.promptIntelligence.preferredPlatforms.length > 0 },
                { label: "Content Formats", filled: f.promptIntelligence.contentFormats.length > 0 },
                { label: "Instruction Overrides", filled: Boolean(f.promptIntelligence.instructionOverrides) },
                { label: "Platform Rules", filled: Boolean(f.promptIntelligence.platformRules) },
            ],
        },
        {
            title: "End-Goal Content Generation",
            layer: "Objective Layer",
            color: "orange",
            items: [
                { label: "Primary Objective", filled: Boolean(f.objectives.primaryObjective) },
                { label: "Content Goal", filled: Boolean(f.objectives.contentGoal) },
                { label: "Campaign Theme", filled: Boolean(f.objectives.campaignTheme) },
                { label: "Call to Action", filled: Boolean(f.objectives.callToAction) },
                { label: "Success Metric", filled: Boolean(f.objectives.successMetric) },
            ],
        },
        {
            title: "Visual Identity Training",
            layer: "Visual Layer",
            color: "pink",
            items: [
                { label: "Primary Color", filled: Boolean(f.visualIdentity.primaryColor) },
                { label: "Secondary Color", filled: Boolean(f.visualIdentity.secondaryColor) },
                { label: "Typography", filled: Boolean(f.visualIdentity.typography) },
                { label: "Brand Mood", filled: Boolean(f.visualIdentity.brandMood) },
                { label: "Visual Style", filled: Boolean(f.visualIdentity.visualStyle) },
                { label: "Reference Creatives", filled: f.visualIdentity.referenceCreatives.length > 0 },
            ],
        },
    ];

    const totalFields = sections.reduce((sum, s) => sum + s.items.length, 0);
    const completedFields = sections.reduce((sum, s) => sum + s.items.filter((i) => i.filled).length, 0);
    const overallPercent = totalFields > 0 ? Math.round((completedFields / totalFields) * 100) : 0;

    return (
        <div className="space-y-6 bg-[#E9E9E966] px-6 pb-6 pt-4">
            {/* Overall Summary */}
            <div className="rounded-2xl border border-primary/20 bg-primary/5 px-6 py-5">
                <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                        <h2 className="text-lg font-bold text-primary">Brand Space Completion</h2>
                        <p className="mt-1 text-sm text-slate-600">
                            {completedFields} of {totalFields} fields completed across all layers
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-4xl font-bold text-primary">{overallPercent}%</p>
                        <p className="text-xs text-slate-500">Overall readiness</p>
                    </div>
                </div>
                <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-primary/10">
                    <div
                        className="h-full rounded-full bg-primary transition-all duration-500"
                        style={{ width: `${overallPercent}%` }}
                    />
                </div>
            </div>

            {/* Per-section review grid */}
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {sections.map((section) => (
                    <ReviewCard key={section.title} section={section} />
                ))}
            </div>

            {overallPercent < 100 && (
                <p className="text-center text-sm text-slate-500">
                    Complete all sections to maximise AI generation quality for this brand.
                </p>
            )}
        </div>
    );
};

export default BrandReview;
