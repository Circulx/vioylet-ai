import {
    FileUploadCollection,
    FormField,
    FormSection,
    StyledInput,
    StyledSelect,
    StyledTextarea,
} from "./FormFields";
import { INDUSTRY_OPTIONS } from "@/lib/brand-space-options";
import {
    createBrandUploadItem,
    normalizeBrandLogoItems,
    updateBrandFormSection,
    type BrandTabProps,
} from "@/types/brand-space.types";

const CoreBrandSignals = ({ brandId, form, setForm, onRemoveUpload }: BrandTabProps) => {
    const updateField = <TKey extends keyof typeof form.core>(key: TKey, value: (typeof form.core)[TKey]) =>
        updateBrandFormSection(setForm, "core", key, value);

    const logoItems = normalizeBrandLogoItems(
        form.core.logos.length ? form.core.logos : form.core.logo ? [form.core.logo] : [],
    );

    const addLogos = (files: FileList | null) => {
        if (!files?.length) {
            return;
        }
        const [file] = Array.from(files);
        if (!file) {
            return;
        }
        const nextLogos = [createBrandUploadItem(file)];
        updateField("logos", nextLogos);
        updateField("logo", nextLogos[0] || null);
    };

    return (
        <FormSection title="Brand Details" className="bg-[#E9E9E966] p-2 px-6 pb-6">
            <FileUploadCollection
                label="Upload Brand Logo"
                acceptedFormats="SVG, PNG, JPG, PDF, PPT, PPTX, JPEG, TXT, DOCX"
                bgColor="bg-[#FFFFFF]"
                items={logoItems}
                onAdd={addLogos}
                multiple={false}
                required
                onRemove={(itemId) => {
                    if (onRemoveUpload) {
                        void onRemoveUpload(itemId);
                        return;
                    }
                    const nextLogos = normalizeBrandLogoItems(logoItems.filter((item) => item.id !== itemId));
                    updateField("logos", nextLogos);
                    updateField("logo", nextLogos[0] || null);
                }}
            />

            <div className="grid gap-5 lg:max-w-md">
                <FormField label="Brand Name" required>
                    <StyledInput
                        placeholder="Enter the brand name"
                        className="bg-section-input-field"
                        value={form.core.name}
                        onChange={(e) => updateField("name", e.target.value)}
                    />
                </FormField>
                <FormField label="Tagline" required>
                    <StyledInput
                        placeholder="Brand tagline"
                        className="bg-section-input-field"
                        value={form.core.tagline}
                        onChange={(e) => updateField("tagline", e.target.value)}
                    />
                </FormField>

                <FormField label="Brand Description" required>
                    <StyledTextarea
                        placeholder="Describe the brand"
                        className="bg-section-input-field"
                        value={form.core.description}
                        onChange={(e) => updateField("description", e.target.value)}
                    />
                </FormField>

                <FormField label="Industry Category" required>
                    <StyledSelect
                        value={form.core.industryCategory}
                        className="bg-section-input-field"
                        onValueChange={(value) => updateField("industryCategory", value)}
                        placeholder="Select the industry category"
                        options={INDUSTRY_OPTIONS}
                        clearable={false}
                    />
                </FormField>

                <FormField label="Key Differentiators">
                    <StyledTextarea
                        placeholder="What makes this brand genuinely different"
                        className="bg-section-input-field"
                        value={form.core.differentiators}
                        onChange={(e) => updateField("differentiators", e.target.value)}
                    />
                </FormField>
            </div>
        </FormSection>
    );
};

export default CoreBrandSignals;
