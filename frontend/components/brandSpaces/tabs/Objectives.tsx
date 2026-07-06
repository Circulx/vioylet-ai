import { FormField, FormSection, FormSubsection, StyledInput, StyledSelect, StyledTextarea } from "./FormFields";
import { updateBrandFormSection, type BrandTabProps } from "@/types/brand-space.types";

const OBJECTIVE_OPTIONS = [
    "brand_awareness",
    "lead_generation",
    "sales_conversion",
    "community_building",
    "product_launch",
    "thought_leadership",
    "customer_retention",
    "employer_branding",
];

const OBJECTIVE_LABELS: Record<string, string> = {
    brand_awareness: "Brand Awareness",
    lead_generation: "Lead Generation",
    sales_conversion: "Sales Conversion",
    community_building: "Community Building",
    product_launch: "Product Launch",
    thought_leadership: "Thought Leadership",
    customer_retention: "Customer Retention",
    employer_branding: "Employer Branding",
};

const CONTENT_GOAL_OPTIONS = [
    "educate",
    "inspire",
    "entertain",
    "convert",
    "inform",
    "engage",
    "nurture",
];

const CONTENT_GOAL_LABELS: Record<string, string> = {
    educate: "Educate",
    inspire: "Inspire",
    entertain: "Entertain",
    convert: "Convert",
    inform: "Inform",
    engage: "Engage",
    nurture: "Nurture",
};

const FREQUENCY_OPTIONS = [
    "daily",
    "3x_week",
    "weekly",
    "biweekly",
    "monthly",
    "campaign_based",
];

const FREQUENCY_LABELS: Record<string, string> = {
    daily: "Daily",
    "3x_week": "3× per week",
    weekly: "Weekly",
    biweekly: "Bi-weekly",
    monthly: "Monthly",
    campaign_based: "Campaign-based",
};

const SUCCESS_METRIC_OPTIONS = [
    "reach",
    "engagement_rate",
    "clicks",
    "conversions",
    "followers",
    "share_of_voice",
    "revenue",
];

const SUCCESS_METRIC_LABELS: Record<string, string> = {
    reach: "Reach / Impressions",
    engagement_rate: "Engagement Rate",
    clicks: "Clicks / CTR",
    conversions: "Conversions",
    followers: "Follower Growth",
    share_of_voice: "Share of Voice",
    revenue: "Revenue Impact",
};

const Objectives = ({ form, setForm }: BrandTabProps) => {
    const updateField = <TKey extends keyof typeof form.objectives>(
        key: TKey,
        value: (typeof form.objectives)[TKey],
    ) => updateBrandFormSection(setForm, "objectives", key, value);

    return (
        <FormSection
            title="End-Goal Content Generation"
            description="Define the outcomes this brand's content should achieve. This drives AI generation toward your real business goals."
            className="bg-[#E9E9E966] px-6 pb-6 pt-2"
        >
            <div className="grid gap-8 lg:grid-cols-2">
                <div className="space-y-6 max-w-md">
                    <FormSubsection title="Primary Objective" className="space-y-4">
                        <FormField label="Primary Objective" className="pb-4">
                            <StyledSelect
                                value={form.objectives.primaryObjective}
                                className="bg-section-input-field"
                                onValueChange={(value) => updateField("primaryObjective", value)}
                                placeholder="Select primary objective"
                                options={OBJECTIVE_OPTIONS}
                                getOptionLabel={(val) => OBJECTIVE_LABELS[val] || val}
                            />
                        </FormField>

                        <FormField label="Content Goal" className="pb-4">
                            <StyledSelect
                                value={form.objectives.contentGoal}
                                className="bg-section-input-field"
                                onValueChange={(value) => updateField("contentGoal", value)}
                                placeholder="Select content goal"
                                options={CONTENT_GOAL_OPTIONS}
                                getOptionLabel={(val) => CONTENT_GOAL_LABELS[val] || val}
                            />
                        </FormField>

                        <FormField label="Campaign Theme" className="pb-4">
                            <StyledInput
                                placeholder="e.g. Summer launch — empowering creators"
                                className="bg-section-input-field"
                                value={form.objectives.campaignTheme}
                                onChange={(e) => updateField("campaignTheme", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Business Outcome" className="pb-4">
                            <StyledTextarea
                                placeholder="Describe the specific business outcome this content should support"
                                className="bg-section-input-field"
                                value={form.objectives.businessOutcome}
                                onChange={(e) => updateField("businessOutcome", e.target.value)}
                            />
                        </FormField>
                    </FormSubsection>
                </div>

                <div className="space-y-6 max-w-md">
                    <FormSubsection title="Conversion & Measurement" className="space-y-4">
                        <FormField label="Call to Action" className="pb-4">
                            <StyledInput
                                placeholder="e.g. Sign up for free, Download the guide, Book a demo"
                                className="bg-section-input-field"
                                value={form.objectives.callToAction}
                                onChange={(e) => updateField("callToAction", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Target Conversion Action" className="pb-4">
                            <StyledInput
                                placeholder="e.g. Trial signup, Product purchase, Event registration"
                                className="bg-section-input-field"
                                value={form.objectives.targetConversionAction}
                                onChange={(e) => updateField("targetConversionAction", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Content Frequency" className="pb-4">
                            <StyledSelect
                                value={form.objectives.contentFrequency}
                                className="bg-section-input-field"
                                onValueChange={(value) => updateField("contentFrequency", value)}
                                placeholder="Select content frequency"
                                options={FREQUENCY_OPTIONS}
                                getOptionLabel={(val) => FREQUENCY_LABELS[val] || val}
                            />
                        </FormField>

                        <FormField label="Primary Success Metric" className="pb-4">
                            <StyledSelect
                                value={form.objectives.successMetric}
                                className="bg-section-input-field"
                                onValueChange={(value) => updateField("successMetric", value)}
                                placeholder="Select success metric"
                                options={SUCCESS_METRIC_OPTIONS}
                                getOptionLabel={(val) => SUCCESS_METRIC_LABELS[val] || val}
                            />
                        </FormField>
                    </FormSubsection>
                </div>
            </div>
        </FormSection>
    );
};

export default Objectives;
