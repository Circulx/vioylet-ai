import {
    FormField,
    FormSection,
    FormSubsection,
    StyledInput,
    StyledSelect,
} from "./FormFields";
import {
    CONTENT_COMPLEXITY_OPTIONS,
    CORE_TONE_OPTIONS,
    SENTENCE_LENGTH_OPTIONS,
} from "@/lib/brand-space-options";
import { updateBrandFormSection, type BrandTabProps } from "@/types/brand-space.types";
import { Checkbox } from "@/components/ui/checkbox";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";

const clampToneWeight = (value: number) => Math.max(0, Math.min(100, value));

const VoiceTone = ({ brandId, form, setForm }: BrandTabProps) => {
    const toneWeights = form.voiceTone.coreToneAttributeWeights || {};
    const updateField = <TKey extends keyof typeof form.voiceTone>(
        key: TKey,
        value: (typeof form.voiceTone)[TKey],
    ) => updateBrandFormSection(setForm, "voiceTone", key, value);

    const toggleToneAttribute = (attribute: string, checked: boolean) => {
        setForm((prev) => {
            const currentAttributes = prev.voiceTone.coreToneAttributes;
            const hasAttribute = currentAttributes.includes(attribute);
            const nextAttributes = checked
                ? hasAttribute
                    ? currentAttributes
                    : [...currentAttributes, attribute]
                : currentAttributes.filter((item) => item !== attribute);
            const currentWeights = prev.voiceTone.coreToneAttributeWeights || {};
            const nextWeights = nextAttributes.reduce<Record<string, number>>((weights, item) => {
                weights[item] = typeof currentWeights[item] === "number"
                    ? clampToneWeight(currentWeights[item])
                    : 50;
                return weights;
            }, {});

            return {
                ...prev,
                voiceTone: {
                    ...prev.voiceTone,
                    coreToneAttributes: nextAttributes,
                    coreToneAttributeWeights: nextWeights,
                },
            };
        });
    };

    const updateToneWeight = (tone: string, value: number) => {
        setForm((prev) => {
            if (!prev.voiceTone.coreToneAttributes.includes(tone)) {
                return prev;
            }

            const currentWeights = prev.voiceTone.coreToneAttributeWeights || {};
            const nextWeights = prev.voiceTone.coreToneAttributes.reduce<Record<string, number>>((weights, item) => {
                weights[item] = item === tone
                    ? clampToneWeight(value)
                    : typeof currentWeights[item] === "number"
                        ? clampToneWeight(currentWeights[item])
                        : 50;
                return weights;
            }, {});

            return {
                ...prev,
                voiceTone: {
                    ...prev.voiceTone,
                    coreToneAttributeWeights: nextWeights,
                },
            };
        });
    };

    return (
        <section className="space-y-8">
            <FormSubsection title="Tone Attributes" className="bg-[#E9E9E966] px-6 pb-6">

            <FormField label="Core Tone Attributes" required>
                <div className="space-y-3">
                    {CORE_TONE_OPTIONS.map((option) => {
                        const checked = form.voiceTone.coreToneAttributes.includes(option);
                        const weight = toneWeights[option] ?? 50;

                        return (
                            <div key={option} className="space-y-4">
                                <Label className="flex items-center gap-3 text-base text-slate-700">
                                    <Checkbox
                                        checked={checked}
                                        onCheckedChange={(nextChecked) => toggleToneAttribute(option, nextChecked === true)}
                                        className="border border-slate-300 data-[state=checked]:border-primary"
                                    />
                                    <span>{option}</span>
                                    {checked ? <span className="text-sm font-medium text-slate-500">{weight}%</span> : null}
                                </Label>
                                {checked ? (
                                    <Slider
                                        value={[weight]}
                                        min={0}
                                        max={100}
                                        step={1}
                                        aria-label={`${option} tone percentage`}
                                        onValueChange={(value) => updateToneWeight(option, value[0])}
                                        className="w-40"
                                    />
                                ) : null}
                            </div>
                        );
                    })}
                </div>
            </FormField>
            </FormSubsection>

            <FormSubsection title="Advanced" description="Optional fields to further refine your brand intelligence" className="bg-[#E9E9E966] px-6 pb-6">
                <div className="grid gap-5 grid-cols-1 md:grid-cols-2">
                    <div className="space-y-5 max-w-md">
                        <FormField label="Primary Emotion">
                            <StyledInput
                            className="bg-section-input-field"
                                placeholder="The dominant feeling this brand creates"
                                value={form.voiceTone.primaryEmotion}
                                onChange={(e) => updateField("primaryEmotion", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Secondary Emotion">
                            <StyledInput
                            className="bg-section-input-field"
                                placeholder="The supporting emotional layer"
                                value={form.voiceTone.secondaryEmotion}
                                onChange={(e) => updateField("secondaryEmotion", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Avoided Emotion">
                            <StyledInput
                            className="bg-section-input-field"
                                placeholder="What this brand never wants to make people feel"
                                value={form.voiceTone.avoidedEmotion}
                                onChange={(e) => updateField("avoidedEmotion", e.target.value)}
                            />
                        </FormField>
                    </div>
                    <div className="space-y-5 max-w-md">
                        <FormField label="Content Complexity">
                            <StyledSelect
                            className="bg-section-input-field"
                                value={form.voiceTone.contentComplexity}
                                onValueChange={(value) => updateField("contentComplexity", value)}
                                placeholder="Select content complexity"
                                options={CONTENT_COMPLEXITY_OPTIONS}
                            />
                        </FormField>

                        <FormField label="Sentence Length">
                            <StyledSelect
                            className="bg-section-input-field"
                                value={form.voiceTone.sentenceLength}
                                onValueChange={(value) => updateField("sentenceLength", value)}
                                placeholder="Select sentence length"
                                options={SENTENCE_LENGTH_OPTIONS}
                            />
                        </FormField>

                    </div>


                    {/* <FormField label="Perspective">
            <StyledSelect
              value={form.voiceTone.perspective}
              onValueChange={(value) => updateField("perspective", value)}
              placeholder="Select perspective"
              options={PERSPECTIVE_OPTIONS}
            />
          </FormField> */}
                </div>
            </FormSubsection>
        </section>
    );
};

export default VoiceTone;
