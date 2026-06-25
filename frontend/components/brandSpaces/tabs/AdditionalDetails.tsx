import { Button } from "@/components/ui/button";
import { FormField, FormSection, FormSubsection, StyledInput, StyledSelect, StyledTextarea } from "./FormFields";
import {
    BRAND_ARCHETYPE_OPTIONS,
    BUYING_STAGE_OPTIONS,
    COMPLIANCE_LEVEL_OPTIONS,
    MARKET_MATURITY_OPTIONS,
} from "@/lib/brand-space-options";
import { updateBrandFormSection, type BrandTabProps, type CompetitorBrandField } from "@/types/brand-space.types";
import { PlusCircle, X } from "lucide-react";

const emptyCompetitorBrand = (): CompetitorBrandField => ({
    name: "",
    websiteUrl: "",
    linkedin: "",
    instagram: "",
    x: "",
});

const AdditionalDetails = ({ form, setForm }: BrandTabProps) => {
    const updateField = <TKey extends keyof typeof form.additional>(
        key: TKey,
        value: (typeof form.additional)[TKey],
    ) => updateBrandFormSection(setForm, "additional", key, value);

    const competitors = form.additional.competitorBrands?.length
        ? form.additional.competitorBrands
        : [
            {
                name: form.additional.competitorBrandName,
                websiteUrl: form.additional.websiteUrl,
                linkedin: form.additional.linkedin,
                instagram: form.additional.instagram,
                x: form.additional.x,
            },
        ];

    const updateCompetitors = (nextCompetitors: CompetitorBrandField[]) => {
        const [primaryCompetitor] = nextCompetitors;
        updateBrandFormSection(setForm, "additional", "competitorBrands", nextCompetitors);
        updateBrandFormSection(setForm, "additional", "competitorBrandName", primaryCompetitor?.name || "");
        updateBrandFormSection(setForm, "additional", "websiteUrl", primaryCompetitor?.websiteUrl || "");
        updateBrandFormSection(setForm, "additional", "linkedin", primaryCompetitor?.linkedin || "");
        updateBrandFormSection(setForm, "additional", "instagram", primaryCompetitor?.instagram || "");
        updateBrandFormSection(setForm, "additional", "x", primaryCompetitor?.x || "");
    };

    const updateCompetitor = <TKey extends keyof CompetitorBrandField>(
        index: number,
        key: TKey,
        value: CompetitorBrandField[TKey],
    ) => {
        const nextCompetitors = competitors.map((competitor, itemIndex) =>
            itemIndex === index ? { ...competitor, [key]: value } : competitor,
        );
        updateCompetitors(nextCompetitors);
    };

    const addCompetitor = () => {
        if (competitors.length >= 3) {
            return;
        }
        updateCompetitors([...competitors, emptyCompetitorBrand()]);
    };

    const removeCompetitor = (index: number) => {
        updateCompetitors(competitors.filter((_, itemIndex) => itemIndex !== index));
    };

    return (
        <FormSection title="Advanced" description="Optional fields to further refine your brand intelligence"
            className="bg-[#E9E9E966] px-6 pb-6 pt-2"
        >
            <div className="grid gap-8 lg:grid-cols-2">
                <div className="space-y-6 max-w-md">
                    <FormSubsection className="space-y-4" title="Brand Purpose and Positioning">
                        <FormField label="Brand Mission" className="pb-4">
                            <StyledInput
                                placeholder="Why this brand exists"
                                className="bg-section-input-field"
                                value={form.additional.brandMission}
                                onChange={(e) => updateField("brandMission", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Brand Vision" className="pb-4">
                            <StyledInput
                                placeholder="Where this brand is headed"
                                className="bg-section-input-field"
                                value={form.additional.brandVision}
                                onChange={(e) => updateField("brandVision", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Brand Promise" className="pb-4">
                            <StyledInput
                                placeholder="What this brand commits to every time"
                                className="bg-section-input-field"
                                value={form.additional.brandPromise}
                                onChange={(e) => updateField("brandPromise", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Market Positioning" className="pb-4">
                            <StyledInput
                                placeholder="How this brand stands apart in the market"
                                className="bg-section-input-field"
                                value={form.additional.marketPositioning}
                                onChange={(e) => updateField("marketPositioning", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Role of Digital Platforms" className="pb-4">
                            <StyledInput
                                placeholder="How digital platforms support the brand"
                                className="bg-section-input-field"
                                value={form.additional.roleOfDigitalPlatforms}
                                onChange={(e) => updateField("roleOfDigitalPlatforms", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Social Media Challenges" className="pb-4">
                            <StyledInput
                                placeholder="Key challenges faced on social media"
                                className="bg-section-input-field"
                                value={form.additional.socialMediaChallenges}
                                onChange={(e) => updateField("socialMediaChallenges", e.target.value)}
                            />
                        </FormField>
                    </FormSubsection>

                    <FormSubsection className="space-y-8" title="Strategic Block">
                        <FormField label="Business Problem or Opportunity" className="pb-4">
                            <StyledInput
                                placeholder="The gap this brand was built to close"
                                className="bg-section-input-field"
                                value={form.additional.businessProblemOrOpportunity}
                                onChange={(e) => updateField("businessProblemOrOpportunity", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Perception Challenge" className="pb-4">
                            <StyledInput
                                placeholder="What people actually feel before they find this brand"
                                className="bg-section-input-field"
                                value={form.additional.perceptionChallenge}
                                onChange={(e) => updateField("perceptionChallenge", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Human Insight" className="pb-4">
                            <StyledInput
                                placeholder="The truth that makes this strategy work"
                                className="bg-section-input-field"
                                value={form.additional.humanInsight}
                                onChange={(e) => updateField("humanInsight", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Brand Advantage" className="pb-4">
                            <StyledInput
                                placeholder="Why this brand wins"
                                className="bg-section-input-field"
                                value={form.additional.brandAdvantage}
                                onChange={(e) => updateField("brandAdvantage", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Strategy" className="pb-4">
                            <StyledTextarea
                                placeholder="How the brand plans to win"
                                className="bg-section-input-field"
                                value={form.additional.strategy}
                                onChange={(e) => updateField("strategy", e.target.value)}
                            />
                        </FormField>
                    </FormSubsection>
                </div>

                <div className="space-y-6 max-w-md">
                    <FormSubsection className="space-y-4" title="Industry and Context Parameters">
                        {/* <FormField label="Market Maturity">
              <StyledSelect
                value={form.additional.marketMaturity}
                onValueChange={(value) => updateField("marketMaturity", value)}
                placeholder="Select market maturity"
                options={MARKET_MATURITY_OPTIONS}
              />
            </FormField> */}
                        <FormField label="Brand Archetype" className="pb-4">
                            <StyledSelect
                                value={form.additional.brandArchetype}
                                className="bg-section-input-field"
                                onValueChange={(value) => updateField("brandArchetype", value)}
                                placeholder="Select brand archetype"
                                options={BRAND_ARCHETYPE_OPTIONS}
                            />
                        </FormField>
                        {/* <FormField label="Buying Stage">
              <StyledSelect
                value={form.additional.buyingStage}
                onValueChange={(value) => updateField("buyingStage", value)}
                placeholder="Select buying stage"
                options={BUYING_STAGE_OPTIONS}
              />
            </FormField> */}
                        <FormField label="Compliance Level" className="pb-4">
                            <StyledSelect
                                value={form.additional.complianceLevel}
                                className="bg-section-input-field"
                                onValueChange={(value) => updateField("complianceLevel", value)}
                                placeholder="Select compliance sensitivity"
                                options={COMPLIANCE_LEVEL_OPTIONS}
                            />
                        </FormField>

                        <div className="space-y-6">
                            <div className="flex justify-between items-center">
                                <h1 className="text-lg font-semibold">Competitor Brands</h1>
                                <Button
                                    type="button"
                                    variant="outline"
                                    disabled={competitors.length >= 3}
                                    onClick={addCompetitor}
                                    className="w-8 h-8 bg-none border-none disabled:opacity-40"
                                    aria-label="Add competitor brand"
                                >
                                    <PlusCircle fill="black" className="size-6 text-white" />
                                </Button>
                            </div>

                            {competitors.map((competitor, index) => (
                                <div key={index} className="space-y-5 border-b border-slate-100 pb-6 last:border-b-0 last:pb-0">
                                    <div className="flex items-center justify-between">
                                        <p className="text-sm font-medium text-slate-500">Competitor {index + 1}</p>
                                        {competitors.length > 1 ? (
                                            <Button
                                                type="button"
                                                variant="ghost"
                                                size="icon-sm"
                                                onClick={() => removeCompetitor(index)}
                                                aria-label={`Remove competitor ${index + 1}`}
                                            >
                                                <X className="h-4 w-4" />
                                            </Button>
                                        ) : null}
                                    </div>
                                    <FormField label="Competitor Brand Name">
                                        <StyledInput
                                            placeholder="Enter the competitor brand name"
                                            value={competitor.name}
                                            onChange={(e) => updateCompetitor(index, "name", e.target.value)}
                                            className="bg-section-input-field"
                                        />
                                    </FormField>
                                    <FormField label="Website URL">
                                        <StyledInput
                                            placeholder="Enter the competitor brand's website url"
                                            value={competitor.websiteUrl}
                                            onChange={(e) => updateCompetitor(index, "websiteUrl", e.target.value)}
                                            className="bg-section-input-field"
                                        />
                                    </FormField>

                                    <div className="space-y-5">
                                        <h1>Social Media Profiles</h1>
                                        <FormField>
                                            <StyledInput
                                                placeholder="LinkedIn"
                                                value={competitor.linkedin}
                                                onChange={(e) => updateCompetitor(index, "linkedin", e.target.value)}
                                                className="bg-section-input-field"
                                            />
                                        </FormField>
                                        <FormField>
                                            <StyledInput
                                                placeholder="Instagram"
                                                value={competitor.instagram}
                                                onChange={(e) => updateCompetitor(index, "instagram", e.target.value)}
                                                className="bg-section-input-field"
                                            />
                                        </FormField>
                                        <FormField>
                                            <StyledInput
                                                placeholder="X"
                                                value={competitor.x}
                                                onChange={(e) => updateCompetitor(index, "x", e.target.value)}
                                                className="bg-section-input-field"
                                            />
                                        </FormField>
                                    </div>
                                </div>
                            ))}

                        </div>
                    </FormSubsection>
                </div>
            </div>
        </FormSection>
    );
};

export default AdditionalDetails;
