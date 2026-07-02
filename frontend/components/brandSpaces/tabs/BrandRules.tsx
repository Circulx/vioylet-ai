import {
    CheckboxList,
    FileUploadCollection,
    FormField,
    FormSection,
    FormSubsection,
    StyledTextarea,
} from "./FormFields";
import { BRAND_RULE_OPTIONS } from "@/lib/brand-space-options";
import { createBrandUploadItem, updateBrandFormSection, type BrandTabProps } from "@/types/brand-space.types";

const BrandRules = ({ form, setForm, onRemoveUpload }: BrandTabProps) => {
    const updateField = <TKey extends keyof typeof form.brandRules>(
        key: TKey,
        value: (typeof form.brandRules)[TKey],
    ) => updateBrandFormSection(setForm, "brandRules", key, value);

    const toggleRule = (value: string) => {
        const nextRules = form.brandRules.selectedRules.includes(value)
            ? form.brandRules.selectedRules.filter((item) => item !== value)
            : [...form.brandRules.selectedRules, value];
        updateField("selectedRules", nextRules);
    };

    const addUploads = (
        key: "positiveWordBankUploads" | "replaceableWordUploads" | "negativeWordBankUploads",
        files: FileList | null,
    ) => {
        if (!files?.length) {
            return;
        }
        updateField(key, [...form.brandRules[key], ...Array.from(files).map((file) => createBrandUploadItem(file))]);
    };

    return (
        <section className="space-y-8" >
            <FormSubsection title={<span>Set The Rules. Violyt Will Follow Them. <span className="text-red-500">*</span></span>}
                className="bg-[#E9E9E966] px-6 pb-6"
            >
                <div className="mt-2">
                    <CheckboxList options={BRAND_RULE_OPTIONS} values={form.brandRules.selectedRules} onToggle={toggleRule} />
                </div>
            </FormSubsection>

            <div className="grid gap-8 lg:grid-cols-2">
                <div className="space-y-5 w-full bg-[#E9E9E966] px-6 pb-6">
                    <FormSubsection title="Brand Word Banks"
                        className=" max-w-md"
                    >
                        <FormField label="Positive Word Bank" info="Enter words or phrases separated by commas" required>
                            <StyledTextarea
                                placeholder="Words and phrases that feel right for this brand"
                                className="bg-section-input-field"
                                value={form.brandRules.positiveWordBank}
                                onChange={(e) => updateField("positiveWordBank", e.target.value)}
                            />
                        </FormField>
                        <FileUploadCollection
                            label="Upload Positive Word Bank"
                            acceptedFormats="PDF, DOC, DOCX, PNG, JPG, JPEG"
                            bgColor="bg-section-input-field"
                            items={form.brandRules.positiveWordBankUploads}
                            onAdd={(files) => addUploads("positiveWordBankUploads", files)}
                            onRemove={(itemId) => {
                                if (onRemoveUpload) {
                                    void onRemoveUpload(itemId);
                                    return;
                                }
                                updateField(
                                    "positiveWordBankUploads",
                                    form.brandRules.positiveWordBankUploads.filter((item) => item.id !== itemId),
                                );
                            }}
                        />

                        <FormField label="Replaceable Words" info="Enter words to replace followed by preferred alternatives, separated by commas. Use format: word - alternative"
                            required>
                            <StyledTextarea
                                placeholder="Words to rephrase, with preferred alternatives"
                                className="bg-section-input-field"
                                value={form.brandRules.replaceableWords}
                                onChange={(e) => updateField("replaceableWords", e.target.value)}
                            />
                        </FormField>
                        <FileUploadCollection
                            label="Upload Replaceable Words"
                            acceptedFormats="PDF, DOC, DOCX, PNG, JPG, JPEG"
                            bgColor="bg-section-input-field"
                            items={form.brandRules.replaceableWordUploads}
                            onAdd={(files) => addUploads("replaceableWordUploads", files)}
                            onRemove={(itemId) => {
                                if (onRemoveUpload) {
                                    void onRemoveUpload(itemId);
                                    return;
                                }
                                updateField(
                                    "replaceableWordUploads",
                                    form.brandRules.replaceableWordUploads.filter((item) => item.id !== itemId),
                                );
                            }}
                        />

                        <FormField label="Negative Word Bank"
                            info="Enter words or phrases separated by commas"
                            required>
                            <StyledTextarea
                                placeholder="Words this brand always avoids"
                                className="bg-section-input-field"
                                value={form.brandRules.negativeWordBank}
                                onChange={(e) => updateField("negativeWordBank", e.target.value)}
                            />
                        </FormField>
                        <FileUploadCollection
                            label="Upload Negative Word Bank"
                            acceptedFormats="PDF, DOC, DOCX, PNG, JPG, JPEG"
                            bgColor="bg-section-input-field"
                            items={form.brandRules.negativeWordBankUploads}
                            onAdd={(files) => addUploads("negativeWordBankUploads", files)}
                            onRemove={(itemId) => {
                                if (onRemoveUpload) {
                                    void onRemoveUpload(itemId);
                                    return;
                                }
                                updateField(
                                    "negativeWordBankUploads",
                                    form.brandRules.negativeWordBankUploads.filter((item) => item.id !== itemId),
                                );
                            }}
                        />
                    </FormSubsection>
                </div>

                <div className="space-y-5 bg-[#E9E9E966] px-6 pb-6">
                    <FormSubsection title="Custom Rules" className="max-w-md">
                        <FormField label="What To Do" info="Add concise, actionable rules. Avoid vague instructions." required>
                            <StyledTextarea
                                placeholder="Behaviours the AI must always apply"
                                value={form.brandRules.whatToDo}
                                onChange={(e) => updateField("whatToDo", e.target.value)}
                                className="bg-section-input-field"
                            />
                        </FormField>
                        <FormField label="What NOT To Do" info="Define clear restrictions. Avoid broad or subjective rules." required>
                            <StyledTextarea
                                placeholder="Behaviours the AI must never replicate"
                                className="bg-section-input-field"
                                value={form.brandRules.whatNotToDo}
                                onChange={(e) => updateField("whatNotToDo", e.target.value)}
                            />
                        </FormField>
                    </FormSubsection>

                    <FormSubsection title="Forbidden Prompt Patterns" className="max-w-md">
                        <FormField label="Restricted Topics" required>
                            <StyledTextarea
                                placeholder="Topics the AI must avoid generating content about."
                                className="bg-section-input-field"
                                value={form.brandRules.restrictedTopics}
                                onChange={(e) => updateField("restrictedTopics", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Restricted Claims" required>
                            <StyledTextarea
                                placeholder="Claims or statements the AI must not make"
                                className="bg-section-input-field"
                                value={form.brandRules.restrictedClaims}
                                onChange={(e) => updateField("restrictedClaims", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Blocked Words / Phrases" required>
                            <StyledTextarea
                                placeholder="Words or phrases the AI must not use"
                                className="bg-section-input-field"
                                value={form.brandRules.blockedWordsPhrases}
                                onChange={(e) => updateField("blockedWordsPhrases", e.target.value)}
                            />
                        </FormField>
                    </FormSubsection>
                </div>
            </div>
        </section>
    );
};

export default BrandRules;
