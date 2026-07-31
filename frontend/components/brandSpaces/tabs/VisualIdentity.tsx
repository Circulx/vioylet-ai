import { type ChangeEvent, type KeyboardEvent, useRef, useState } from "react";
import Image from "next/image";
import { FileText, Trash2, UploadCloud, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
    AddMoreButton,
    AdditionalColorRow,
    ColorHexInput,
    FontPickerField,
    FileUploadField,
    FileUploadCollection,
    FormField,
    FormSection,
    FormSubsection,
    StyledInput,
    StyledTextarea,
} from "./FormFields";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { useGoogleFonts } from "@/hooks/useGoogleFonts";
import { stripFileExtension } from "@/lib/file-utils";
import { LOGO_PLACEMENT_OPTIONS } from "@/lib/brand-space-options";
import {
    createBrandUploadItem,
    updateBrandFormSection,
    type BrandTabProps,
    type BrandUploadItem,
} from "@/types/brand-space.types";

const COLOR_GUIDE_FORMATS = "DOCX, PDF";
const FONT_UPLOAD_FORMATS = "TTF, OTF, WOFF, WOFF2";
const FONT_GUIDE_FORMATS = "DOCX/PDF";
const METADATA_UPLOAD_FORMATS = "PDF, JPG, PNG, DOCX";
const MAX_METADATA_FILE_SIZE_MB = 25;

type VisualMetadataUpload = {
    item: BrandUploadItem;
    tagDraft: string;
};

const VisualIdentity = ({ form, setForm, onRemoveUpload, onSelectColorPaletteUpload }: BrandTabProps) => {
    const googleFontsQuery = useGoogleFonts();

    const updateField = <TKey extends keyof typeof form.visualIdentity>(
        key: TKey,
        value: (typeof form.visualIdentity)[TKey],
    ) => updateBrandFormSection(setForm, "visualIdentity", key, value);

    const addUploads = (key: "colorPaletteUploads", files: FileList | null) => {
        if (!files?.length) {
            return;
        }
        updateField(key, [...form.visualIdentity[key], ...Array.from(files).map((file) => createBrandUploadItem(file))]);
    };

    const addFontUploads = (files: FileList | null) => {
        if (!files?.length) {
            return;
        }

        const nextFiles = Array.from(files);
        const nextUploads = nextFiles.map((file) => createBrandUploadItem(file, ["Font"]));
        updateField("uploadedFonts", [...form.visualIdentity.uploadedFonts, ...nextUploads]);

        const [firstFile] = nextFiles;
        if (firstFile) {
            updateField("typography", stripFileExtension(firstFile.name));
        }
    };

    const fontStyleGuideItem = form.visualIdentity.fontStyleGuide[0] || null;

    const replaceFontStyleGuide = (files: FileList | null) => {
        if (!files?.length) {
            return;
        }

        const [file] = Array.from(files);
        if (!file) {
            return;

        }

        updateField("fontStyleGuide", [createBrandUploadItem(file, ["Font Guide"])]);
    };

    return (
        <section >
            <FormSubsection title="Brand Visual Guidelines"
            className="bg-[#E9E9E966] px-6 pt-2 pb-6"
            >

            <div className="grid gap-8 lg:grid-cols-2">
                <div className="space-y-5 max-w-md">
                        <FormField label="Brand Mood">
                            <StyledTextarea
                                className="bg-section-input-field"
                                placeholder="Overall mood the brand conveys"
                                value={form.visualIdentity.brandMood}
                                onChange={(e) => updateField("brandMood", e.target.value)}
                            />
                        </FormField>
                        <FormField label="Visual Style">
                            <StyledTextarea
                                className="bg-section-input-field"
                                placeholder="Visual style the brand uses"
                                value={form.visualIdentity.visualStyle}
                                onChange={(e) => updateField("visualStyle", e.target.value)}
                            />
                        </FormField>

                        <FormField label="Logo Placement" description="Select one logo placement" required>
                            <RadioGroup
                                value={form.visualIdentity.logoPlacements[0] || ""}
                                onValueChange={(value) => updateField("logoPlacements", [value])}
                            >
                                {LOGO_PLACEMENT_OPTIONS.map((option) => (
                                    <Label key={option} className="flex items-center gap-3 text-base text-slate-700">
                                        <RadioGroupItem value={option} />
                                        <span>{option}</span>
                                    </Label>
                                ))}
                            </RadioGroup>
                        </FormField>
                </div>

                <div className="space-y-5 max-w-md">
                    <div className="flex flex-col gap-3">
                        <h1 className="text-base font-medium text-[#121212]">
                            Brand Color Palette (HEX)<span className="ml-1 text-red-500">*</span>
                        </h1>
                        <div className="grid gap-3 md:grid-cols-2">
                            <div className="flex h-12 items-center rounded-xl bg-section-input-field px-4 py-3 text-sm text-[#2C2C2C]">
                                Primary color
                            </div>
                            <ColorHexInput
                                value={form.visualIdentity.primaryColor}
                                onValueChange={(value) => updateField("primaryColor", value)}
                                className="rounded-xl bg-section-input-field"
                            />
                        </div>
                        <div className="grid gap-3 md:grid-cols-2">
                            <div className="flex h-12 items-center rounded-xl bg-section-input-field px-4 py-3 text-sm text-[#2C2C2C]">
                                Secondary color
                            </div>
                            <ColorHexInput
                                value={form.visualIdentity.secondaryColor}
                                onValueChange={(value) => updateField("secondaryColor", value)}
                                className="rounded-xl bg-section-input-field"
                            />
                        </div>
                        {form.visualIdentity.additionalColors.map((color, index) => (
                            <AdditionalColorRow
                                key={`additional-color-${index}`}
                                name={color.name}
                                hex={color.hex}
                                onNameChange={(value) => {
                                    const nextColors = [...form.visualIdentity.additionalColors];
                                    nextColors[index] = { ...nextColors[index], name: value };
                                    updateField("additionalColors", nextColors);
                                }}
                                onHexChange={(value) => {
                                    const nextColors = [...form.visualIdentity.additionalColors];
                                    nextColors[index] = { ...nextColors[index], hex: value };
                                    updateField("additionalColors", nextColors);
                                }}
                                canRemove={form.visualIdentity.additionalColors.length > 1}
                                onRemove={() =>
                                    updateField(
                                        "additionalColors",
                                        form.visualIdentity.additionalColors.filter((_, itemIndex) => itemIndex !== index),
                                    )
                                }
                            />
                        ))}
                        <div className="flex justify-end">
                            <AddMoreButton
                                onClick={() =>
                                    updateField("additionalColors", [...form.visualIdentity.additionalColors, { name: "", hex: "" }])
                                }
                            />
                        </div>
                    </div>

                    <FileUploadCollection
                        label="Upload Color Palette"
                        acceptedFormats={COLOR_GUIDE_FORMATS}
                        bgColor="bg-[#FFFFFF]"
                        items={form.visualIdentity.colorPaletteUploads}
                        onAdd={(files) => addUploads("colorPaletteUploads", files)}
                        activeItemId={form.visualIdentity.activeColorPaletteUploadId}
                        onSelect={onSelectColorPaletteUpload}
                        onRemove={(itemId) => {
                            if (onRemoveUpload) {
                                void onRemoveUpload(itemId);
                                return;
                            }
                            updateField(
                                "colorPaletteUploads",
                                form.visualIdentity.colorPaletteUploads.filter((item) => item.id !== itemId),
                            );
                        }}
                    />

                    <FontPickerField
                        label="Font"
                        required
                        placeholder="Upload or Select Font"
                        value={form.visualIdentity.typography}
                        options={googleFontsQuery.data || []}
                        isLoading={googleFontsQuery.isLoading}
                        error={googleFontsQuery.error instanceof Error ? googleFontsQuery.error.message : null}
                        acceptedFormats={FONT_UPLOAD_FORMATS}
                        uploadedItems={form.visualIdentity.uploadedFonts}
                        onValueChange={(value) => updateField("typography", value)}
                        onUpload={addFontUploads}
                        onRemoveUpload={(itemId) => {
                            if (onRemoveUpload) {
                                void onRemoveUpload(itemId);
                                return;
                            }
                            updateField(
                                "uploadedFonts",
                                form.visualIdentity.uploadedFonts.filter((item) => item.id !== itemId),
                            );
                        }}
                    />

                    <FileUploadField
                        label="Upload Font Style Guide"
                        acceptedFormats={FONT_GUIDE_FORMATS}
                        // required
                        uploadLabel="Upload"
                        item={fontStyleGuideItem}
                        onChange={replaceFontStyleGuide}
                        onRemove={() => {
                            if (onRemoveUpload) {
                                if (fontStyleGuideItem) {
                                    void onRemoveUpload(fontStyleGuideItem.id);
                                }
                                return;
                            }
                            updateField("fontStyleGuide", []);
                        }}
                    />
                </div>


            </div>
            </FormSubsection>
                <FormSubsection title="Upload documentation"
                        className=" mt-6 bg-[#E9E9E966] px-6 pt-2 pb-6"
                    >
                        <VisualMetadataUploadField
                            label="Reference creatives"
                            required
                            items={form.visualIdentity.referenceCreatives}
                            onAddItems={(items) => updateField("referenceCreatives", [...form.visualIdentity.referenceCreatives, ...items])}
                            onRemove={(itemId) => {
                                if (onRemoveUpload) {
                                    void onRemoveUpload(itemId);
                                    return;
                                }
                                updateField(
                                    "referenceCreatives",
                                    form.visualIdentity.referenceCreatives.filter((item) => item.id !== itemId),
                                );
                            }}
                        />
                        <div className="h-2" />
                        <VisualMetadataUploadField
                            label="Mood boards"
                            required
                            items={form.visualIdentity.moodBoards}
                            onAddItems={(items) => updateField("moodBoards", [...form.visualIdentity.moodBoards, ...items])}
                            onRemove={(itemId) => {
                                if (onRemoveUpload) {
                                    void onRemoveUpload(itemId);
                                    return;
                                }
                                updateField(
                                    "moodBoards",
                                    form.visualIdentity.moodBoards.filter((item) => item.id !== itemId),
                                );
                            }}
                        />
                    </FormSubsection>
        </section>
    );
};

function VisualMetadataUploadField({
    label,
    required,
    items,
    onAddItems,
    onRemove,
}: {
    label: string;
    required?: boolean;
    items: BrandUploadItem[];
    onAddItems: (items: BrandUploadItem[]) => void;
    onRemove: (itemId: string) => void;
}) {
    const [isOpen, setIsOpen] = useState(false);
    const [pendingUploads, setPendingUploads] = useState<VisualMetadataUpload[]>([]);
    const inputRef = useRef<HTMLInputElement | null>(null);

    const addPendingFiles = (files: FileList | null) => {
        if (!files?.length) {
            return;
        }

        const nextItems = Array.from(files)
            .filter((file) => file.size <= MAX_METADATA_FILE_SIZE_MB * 1024 * 1024)
            .map((file) => ({
                item: createBrandUploadItem(file),
                tagDraft: "",
            }));

        if (!nextItems.length) {
            return;
        }

        setPendingUploads((current) => [...current, ...nextItems]);
    };

    const updatePendingItem = (
        itemId: string,
        updater: (upload: VisualMetadataUpload) => VisualMetadataUpload,
    ) => {
        setPendingUploads((current) =>
            current.map((upload) => (upload.item.id === itemId ? updater(upload) : upload)),
        );
    };

    const commitTags = (itemId: string, value?: string) => {
        updatePendingItem(itemId, (upload) => {
            const nextTags = parseMetadataTags(value ?? upload.tagDraft);
            if (!nextTags.length) {
                return { ...upload, tagDraft: "" };
            }

            return {
                item: {
                    ...upload.item,
                    tags: uniqueMetadataTags([...(upload.item.tags || []), ...nextTags]),
                },
                tagDraft: "",
            };
        });
    };

    const handleTagInputChange = (itemId: string, value: string) => {
        if (!value.includes(",")) {
            updatePendingItem(itemId, (upload) => ({ ...upload, tagDraft: value }));
            return;
        }

        const parts = value.split(",");
        const draft = parts.pop() || "";
        const completedTags = parseMetadataTags(parts.join(","));
        updatePendingItem(itemId, (upload) => ({
            item: {
                ...upload.item,
                tags: uniqueMetadataTags([...(upload.item.tags || []), ...completedTags]),
            },
            tagDraft: draft,
        }));
    };

    const handleTagKeyDown = (event: KeyboardEvent<HTMLInputElement>, itemId: string) => {
        if (event.key !== "Enter") {
            return;
        }

        event.preventDefault();
        commitTags(itemId);
    };

    const removePendingTag = (itemId: string, tag: string) => {
        updatePendingItem(itemId, (upload) => ({
            ...upload,
            item: {
                ...upload.item,
                tags: (upload.item.tags || []).filter((itemTag) => itemTag !== tag),
            },
        }));
    };

    const handleUploadAll = () => {
        const finalizedItems = pendingUploads.map((upload) => ({
            ...upload.item,
            tags: uniqueMetadataTags([...(upload.item.tags || []), ...parseMetadataTags(upload.tagDraft)]),
        }));

        onAddItems(finalizedItems);
        setPendingUploads([]);
        setIsOpen(false);
    };

    const handleOpenChange = (open: boolean) => {
        setIsOpen(open);
        if (!open) {
            setPendingUploads([]);
        }
    };

    return (
        <div className="space-y-3">
            <div>
                <p className="text-base font-medium text-black">
                    {label}
                    {required ? <span className="ml-1 text-red-500">*</span> : null}
                </p>
                <p className="text-sm text-slate-500">Formats accepted: {METADATA_UPLOAD_FORMATS}</p>
            </div>

            <div className="flex flex-wrap gap-4 max-h-[300px] overflow-y-auto">
                <Button
                    type="button"
                    onClick={() => setIsOpen(true)}
                    className="flex h-20 w-60 flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#E5E4E4] bg-white text-sm text-slate-600 transition hover:border-primary/40 hover:bg-slate-50"
                >
                    <UploadCloud className="mb-2 h-4 w-4" />
                    Upload
                </Button>
                {items.map((item) => (
                    <VisualMetadataUploadedFileCard key={item.id} item={item} onRemove={() => onRemove(item.id)} />
                ))}
            </div>

            <Dialog open={isOpen} onOpenChange={handleOpenChange}>
                <DialogContent className="max-h-[90vh] w-full max-w-5xl overflow-y-auto border-none bg-white p-0 shadow-xl" showCloseButton>
                    <DialogTitle className="sr-only">Upload {label} files</DialogTitle>
                    <div className="mx-auto my-8 w-[88%] rounded-sm bg-[#F4F4F4] px-8 py-6">
                        <div className="mx-auto max-w-[400px] space-y-7">
                            <h3 className="text-base font-bold text-[#121212]">Upload File:</h3>

                            <Button
                                type="button"
                                onClick={() => inputRef.current?.click()}
                                className="flex h-36 w-full flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#D8E2EC] bg-white text-sm text-[#8191A7] transition hover:border-[#56BBD1]"
                            >
                                <span className="mb-5 rounded-4xl bg-[#52B2CF21] p-3">
                                    <Image src="/brandSpaces/upload_cloud.svg" alt="Upload file icon" width={33} height={33} />
                                </span>
                                {METADATA_UPLOAD_FORMATS} (Max {MAX_METADATA_FILE_SIZE_MB}MB per file)
                            </Button>
                            <input
                                ref={inputRef}
                                type="file"
                                multiple
                                className="hidden"
                                accept={acceptedFormatsToAccept(METADATA_UPLOAD_FORMATS)}
                                onChange={(event: ChangeEvent<HTMLInputElement>) => {
                                    addPendingFiles(event.target.files);
                                    event.currentTarget.value = "";
                                }}
                            />

                            <div className="space-y-7">
                                {pendingUploads.map((upload) => (
                                    <VisualPendingUploadCard
                                        key={upload.item.id}
                                        upload={upload}
                                        onDelete={() =>
                                            setPendingUploads((current) => current.filter((item) => item.item.id !== upload.item.id))
                                        }
                                        onTagChange={(value) => handleTagInputChange(upload.item.id, value)}
                                        onTagKeyDown={(event) => handleTagKeyDown(event, upload.item.id)}
                                        onTagBlur={() => commitTags(upload.item.id)}
                                        onRemoveTag={(tag) => removePendingTag(upload.item.id, tag)}
                                    />
                                ))}
                            </div>

                            {pendingUploads.length ? (
                                <div className="flex justify-center pt-1">
                                    <Button
                                        type="button"
                                        onClick={handleUploadAll}
                                        className="h-14 rounded-none bg-primary px-10 text-lg font-medium text-white hover:bg-[#36237E]"
                                    >
                                        Upload All
                                        <Image src="/brandSpaces/document-upload.svg" alt="Upload files icon" width={20} height={20} className="ml-2" />
                                    </Button>
                                </div>
                            ) : null}
                        </div>
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}

function VisualPendingUploadCard({
    upload,
    onDelete,
    onTagChange,
    onTagKeyDown,
    onTagBlur,
    onRemoveTag,
}: {
    upload: VisualMetadataUpload;
    onDelete: () => void;
    onTagChange: (value: string) => void;
    onTagKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
    onTagBlur: () => void;
    onRemoveTag: (tag: string) => void;
}) {
    return (
        <div className="bg-white px-6 py-5">
            <div className="flex items-start justify-between gap-4">
                <div className="flex min-w-0 items-center gap-2">
                    <FileText className="h-5 w-5 shrink-0 text-[#F8CF75]" />
                    <p className="truncate text-lg font-medium text-[#2C2C2C]">{upload.item.name}</p>
                </div>
                <button type="button" onClick={onDelete} className="text-[#8A9AAF] transition hover:text-red-500" aria-label="Remove file">
                    <Trash2 className="h-5 w-5" />
                </button>
            </div>

            <p className="mt-4 text-sm text-[#8191A7]">{formatFileSize(upload.item.file?.size)} &bull; Ready</p>
            <div className="mt-2 h-1.5 rounded-full bg-[#EDF3F8]">
                <div className="h-full w-full rounded-full bg-[#58BDD2]" />
            </div>

            {(upload.item.tags || []).length ? (
                <div className="mt-7 flex flex-wrap gap-3">
                    {upload.item.tags?.map((tag) => (
                        <span
                            key={tag}
                            className="inline-flex items-center gap-1 rounded-full bg-[#F1F5F9] px-3 py-1 text-sm text-[#667085]"
                        >
                            {tag}
                            <button type="button" onClick={() => onRemoveTag(tag)} className="text-[#8A9AAF] hover:text-red-500" aria-label={`Remove ${tag} tag`}>
                                <X className="h-3 w-3" />
                            </button>
                        </span>
                    ))}
                </div>
            ) : (
                <div className="mt-5 space-y-2">
                    <p className="text-sm font-medium text-[#8191A7]">Description</p>
                    <Input
                        value={upload.tagDraft}
                        onChange={(event) => onTagChange(event.target.value)}
                        onKeyDown={onTagKeyDown}
                        onBlur={onTagBlur}
                        placeholder="Add description"
                        className="h-12 rounded-xl border-[#DDE7F0] bg-[#F9FBFD] text-sm shadow-none"
                    />
                </div>
            )}

            {(upload.item.tags || []).length ? (
                <Input
                    value={upload.tagDraft}
                    onChange={(event) => onTagChange(event.target.value)}
                    onKeyDown={onTagKeyDown}
                    onBlur={onTagBlur}
                    placeholder="Add metadata"
                    className="mt-4 h-10 rounded-xl border-[#DDE7F0] bg-[#F9FBFD] text-sm shadow-none"
                />
            ) : null}
        </div>
    );
}

function VisualMetadataUploadedFileCard({
    item,
    onRemove,
}: {
    item: BrandUploadItem;
    onRemove: () => void;
}) {
    return (
        <div className="w-40 rounded-xl border border-slate-200 bg-white p-3 shadow-[0_10px_20px_-18px_rgba(15,23,42,0.45)]">
            <div className="flex items-start justify-between gap-2">
                <div className="flex h-7 w-8 items-center justify-center rounded-md bg-primary/8 text-sky-500">
                    <FileText className="h-4 w-4" />
                </div>
                <Button variant="ghost" type="button" className="h-6 w-6 bg-none p-0 text-slate-400 transition hover:bg-none" onClick={onRemove}>
                    <X className="h-4 w-4" />
                </Button>
            </div>
            <p className="mt-3 line-clamp-2 text-xs font-medium text-slate-700">{item.name}</p>
            {item.tags?.length ? (
                <div className="mt-2 flex flex-wrap gap-1">
                    {item.tags.map((tag) => (
                        <span key={tag} className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-500">
                            {tag}
                        </span>
                    ))}
                </div>
            ) : null}
        </div>
    );
}

function parseMetadataTags(value: string) {
    return value
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean);
}

function uniqueMetadataTags(tags: string[]) {
    return Array.from(new Set(tags));
}

function formatFileSize(size?: number) {
    if (!size) {
        return "0 MB";
    }

    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function acceptedFormatsToAccept(value: string) {
    return value
        .split(/[,\s/]+/)
        .map((item) => item.trim().toLowerCase())
        .filter(Boolean)
        .map((item) => `.${item}`)
        .join(",");
}

export default VisualIdentity;
