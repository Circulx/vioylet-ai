import { FormField, FormSection, FormSubsection, StyledInput, StyledTextarea } from "./FormFields";
import { updateBrandFormSection, type BrandTabProps } from "@/types/brand-space.types";

const PLATFORM_OPTIONS = [
    "LinkedIn",
    "Instagram",
    "X (Twitter)",
    "YouTube",
    "Facebook",
    "TikTok",
    "Pinterest",
    "Threads",
];

const FORMAT_OPTIONS = [
    "Short-form post",
    "Long-form article",
    "Carousel",
    "Reel / Short video",
    "Story",
    "Newsletter",
    "Thread",
    "Infographic caption",
];

type Toggle = {
    label: string;
    value: string;
    active: boolean;
    onToggle: () => void;
};

function PillToggle({ label, active, onToggle }: Toggle) {
    return (
        <button
            type="button"
            onClick={onToggle}
            className={`rounded-full border px-3 py-1.5 text-sm font-medium transition-all ${
                active
                    ? "border-primary bg-primary text-white"
                    : "border-[#C5C5C5] bg-white text-slate-600 hover:border-primary/40"
            }`}
        >
            {label}
        </button>
    );
}

const PromptIntelligence = ({ brandId, form, setForm }: BrandTabProps) => {
    const updateField = <TKey extends keyof typeof form.promptIntelligence>(
        key: TKey,
        value: (typeof form.promptIntelligence)[TKey],
    ) => updateBrandFormSection(setForm, "promptIntelligence", key, value);

    const togglePlatform = (platform: string) => {
        const current = form.promptIntelligence.preferredPlatforms;
        const next = current.includes(platform)
            ? current.filter((p) => p !== platform)
            : [...current, platform];
        updateField("preferredPlatforms", next);
    };

    const toggleFormat = (format: string) => {
        const current = form.promptIntelligence.contentFormats;
        const next = current.includes(format)
            ? current.filter((f) => f !== format)
            : [...current, format];
        updateField("contentFormats", next);
    };

    return (
        <FormSection
            title="Prompt Intelligence Setup"
            description="Configure how AI generates content for this brand — platforms, formats, and instruction overrides."
            className="bg-[#E9E9E966] px-6 pb-6 pt-2"
        >
            <div className="grid gap-8 lg:grid-cols-2">
                <div className="space-y-6 max-w-md">
                    <FormSubsection title="Preferred Platforms" className="space-y-3">
                        <p className="text-sm text-slate-500">
                            Select which platforms this brand primarily publishes on.
                        </p>
                        <div className="flex flex-wrap gap-2 pt-1">
                            {PLATFORM_OPTIONS.map((platform) => (
                                <PillToggle
                                    key={platform}
                                    label={platform}
                                    value={platform}
                                    active={form.promptIntelligence.preferredPlatforms.includes(platform)}
                                    onToggle={() => togglePlatform(platform)}
                                />
                            ))}
                        </div>
                    </FormSubsection>

                    <FormSubsection title="Preferred Content Formats" className="space-y-3">
                        <p className="text-sm text-slate-500">
                            Select the content formats this brand typically uses.
                        </p>
                        <div className="flex flex-wrap gap-2 pt-1">
                            {FORMAT_OPTIONS.map((format) => (
                                <PillToggle
                                    key={format}
                                    label={format}
                                    value={format}
                                    active={form.promptIntelligence.contentFormats.includes(format)}
                                    onToggle={() => toggleFormat(format)}
                                />
                            ))}
                        </div>
                    </FormSubsection>
                </div>

                <div className="space-y-6 max-w-md">
                    <FormSubsection title="Instruction Overrides" className="space-y-4">
                        <FormField label="Content Tone Override" className="pb-4">
                            <StyledInput
                                placeholder="e.g. Always end with a question to drive engagement"
                                className="bg-section-input-field"
                                value={form.promptIntelligence.contentTone}
                                onChange={(e) => updateField("contentTone", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Platform-Specific Rules" className="pb-4">
                            <StyledTextarea
                                placeholder="e.g. On LinkedIn: no hashtags in body. On Instagram: max 5 hashtags."
                                className="bg-section-input-field"
                                value={form.promptIntelligence.platformRules}
                                onChange={(e) => updateField("platformRules", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Contextual Hints" className="pb-4">
                            <StyledTextarea
                                placeholder="e.g. Always reference the product launch when relevant. Use a storytelling arc."
                                className="bg-section-input-field"
                                value={form.promptIntelligence.contextualHints}
                                onChange={(e) => updateField("contextualHints", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Instruction Overrides (Global)" className="pb-4">
                            <StyledTextarea
                                placeholder="Any global instructions to override defaults for this brand's content generation"
                                className="bg-section-input-field"
                                value={form.promptIntelligence.instructionOverrides}
                                onChange={(e) => updateField("instructionOverrides", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Formats to Avoid" className="pb-4">
                            <StyledInput
                                placeholder="e.g. Avoid listicles. No click-bait headlines."
                                className="bg-section-input-field"
                                value={form.promptIntelligence.avoidedFormats}
                                onChange={(e) => updateField("avoidedFormats", e.target.value)}
                            />
                        </FormField>
                    </FormSubsection>
                </div>
            </div>
        </FormSection>
    );
};

export default PromptIntelligence;
