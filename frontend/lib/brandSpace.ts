import type { ComponentType } from "react";
import BrandReview from "@/components/brandSpaces/tabs/BrandReview";
import BrandKnowledge from "@/components/brandSpaces/tabs/BrandKnowledge";
import BrandRules from "@/components/brandSpaces/tabs/BrandRules";
import CoreBrandSignals from "@/components/brandSpaces/tabs/CoreBrandSignals";
import Objectives from "@/components/brandSpaces/tabs/Objectives";
import PromptIntelligence from "@/components/brandSpaces/tabs/PromptIntelligence";
import TargetAudience from "@/components/brandSpaces/tabs/TargetAudience";
import VisualIdentity from "@/components/brandSpaces/tabs/VisualIdentity";
import VoiceTone from "@/components/brandSpaces/tabs/VoiceTone";
import IntelligencePipeline from "@/components/brandSpaces/tabs/IntelligencePipeline";
import AdditionalDetails from "@/components/brandSpaces/tabs/AdditionalDetails";
import type { BrandTabProps } from "@/types/brand-space.types";

type BrandSpaceTab = {
    id: number;
    label: string;
    value: string;
    layer: string;
    content: ComponentType<BrandTabProps>;
};

export const brandSpaceTabs: BrandSpaceTab[] = [
    {
        id: 1,
        label: "Brand Space Creation",
        value: "core_brand_signals",
        layer: "Identity Layer",
        content: CoreBrandSignals,
    },
    {
        id: 2,
        label: "Brand Foundations",
        value: "additional_details",
        layer: "Strategic Layer",
        content: AdditionalDetails,
    },
    {
        id: 3,
        label: "Brand Voice & Emotion",
        value: "voice_tone",
        layer: "Tone Layer",
        content: VoiceTone,
    },
    {
        id: 4,
        label: "Audience Persona Mapping",
        value: "target_audience",
        layer: "Persona Intelligence Layer",
        content: TargetAudience,
    },
    {
        id: 5,
        label: "Do's & Don'ts",
        value: "brand_rules",
        layer: "Guardrail Layer",
        content: BrandRules,
    },
    {
        id: 6,
        label: "Brand Knowledge Upload",
        value: "brand_knowledge",
        layer: "Learning Layer",
        content: BrandKnowledge,
    },
    {
        id: 7,
        label: "Prompt Intelligence Setup",
        value: "prompt_intelligence",
        layer: "Instruction Layer",
        content: PromptIntelligence,
    },
    {
        id: 8,
        label: "Content Objectives",
        value: "objectives",
        layer: "Objective Layer",
        content: Objectives,
    },
    {
        id: 9,
        label: "Visual Identity",
        value: "visual_identity",
        layer: "Visual Layer",
        content: VisualIdentity,
    },
    {
        id: 10,
        label: "Review",
        value: "review",
        layer: "Review",
        content: BrandReview,
    },
    {
        id: 11,
        label: "Violyt Intelligence (Beta)",
        value: "intelligence_pipeline",
        layer: "Intelligence Layer",
        content: IntelligencePipeline,
    },
];
