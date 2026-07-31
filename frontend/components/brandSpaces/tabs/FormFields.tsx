"use client";

import { type ComponentProps, ReactNode, useId, useRef, useState } from "react";
import {
    AlertCircle,
    Check,
    CheckCircle2,
    ChevronDown,
    Eye,
    FileText,
    ImagePlus,
    Loader2,
    Pipette,
    Plus,
    Upload,
    X,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { cn } from "@/lib/utils";
import type { BrandUploadItem } from "@/types/brand-space.types";
import { Label } from "@/components/ui/label";
import { InformationTip } from "@/components/InformationTip";
import Image from "next/image";

function AdvancedFieldsTipContent() {
    return (
        <div className="space-y-2 text-left">
            <p className="font-medium text-[#6F6F6F]">Advanced Fields</p>
            <p>For the best results, we recommend completing all Advanced fields. Providing more details helps Violyt generate more accurate, personalized, and higher-quality content.</p>
        </div>
    );
}

export function AdvancedSectionTitle({ showInfo }: { showInfo: boolean }) {
    return (
        <span className="inline-flex items-center">
            <span>Advanced</span>
            {showInfo ? <InformationTip content={<AdvancedFieldsTipContent />} /> : null}
        </span>
    );
}

type FormFieldProps = {
    label?: string;
    required?: boolean;
    children: ReactNode;
    className?: string;
    description?: string;
    info?: string;
    error?: string;
};

type UploadCollectionProps = {
    label: string;
    required?: boolean;
    acceptedFormats: string;
    items: BrandUploadItem[];
    onAdd: (files: FileList | null) => void;
    onRemove: (itemId: string) => void;
    activeItemId?: string;
    onSelect?: (itemId: string) => void;
    multiple?: boolean;
    tags?: string[];
    className?: string;
    bgColor?: string;
};

type SingleUploadProps = {
    label: string;
    acceptedFormats: string;
    item: BrandUploadItem | null;
    onChange: (files: FileList | null) => void;
    onRemove: () => void;
    required?: boolean;
    uploadLabel?: string;
    className?: string;
};

type FontPickerOption = {
    family: string;
    category?: string;
    variants?: string[];
};

type FontPickerFieldProps = {
    label?: string;
    required?: boolean;
    value: string;
    placeholder: string;
    options: FontPickerOption[];
    onValueChange: (value: string) => void;
    acceptedFormats: string;
    uploadedItems: BrandUploadItem[];
    onUpload: (files: FileList | null) => void;
    onRemoveUpload: (itemId: string) => void;
    isLoading?: boolean;
    error?: string | null;
    className?: string;
};

export function FormField({ label, required, children, description, info, error, className }: FormFieldProps) {
    return (
        <div className={cn("block space-y-3", className)}>
            <div>

            <p className="text-base font-medium text-[#121212]">
                {label}
                {required ? <span className="ml-1 mr-2 text-red-500">*</span> : null}
                {info ? <InformationTip content={info} /> : null}
            </p>
                {description ? <p className="text-base text-slate-500 pt-2">{description}</p> : null}
            </div>

            <div className="mt-2">
                {children}
            </div>
            {error ? <p className="text-sm text-red-500">{error}</p> : null}
        </div>
    );
}

export function FormSection({
    title,
    description,
    children,
    className
}: {
    title?: ReactNode;
    description?: string;
    children: ReactNode;
    className?: string;
}) {
    return (
        <div className={cn("space-y-6", className)}>
            <div>
                {title && (
                    <h2 className="text-xl font-semibold text-slate-800 my-2">{title}</h2>
                )}
                {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
            </div>
            <div className="space-y-6">{children}</div>
        </div>
    );
}

export function FormSubsection({
    title,
    description,
    children,
    className,
}: {
    title?: ReactNode;
    description?: string;
    children: ReactNode;
    className?: string;
}) {
    return (
        <section className={cn("space-y-4", className)}>
            <div className="py-4">
                <h2 className="text-xl font-semibold text-black">{title}</h2>
                {description ? <p className="mt-1 text-base text-[#000000C4]">{description}</p> : null}
            </div>
            <div className="space-y-2">
                {children}
            </div>
        </section>
    );
}

export function StyledInput(props: ComponentProps<typeof Input>) {
return (
        <Input
            {...props}
            className={cn(
                "h-12 rounded-xl border-none bg-input-field px-4 py-3 text-sm shadow-none focus-visible:ring-2 focus-visible:ring-primary/20",
                props.className,
            )}
        />
    );
}

function colorPickerValue(value: string) {
    const normalized = value.trim();
    if (/^#[0-9a-fA-F]{6}$/.test(normalized)) {
        return normalized;
    }
    if (/^[0-9a-fA-F]{6}$/.test(normalized)) {
        return `#${normalized}`;
    }
    return "#000000";
}

export function ColorHexInput({
    value,
    onValueChange,
    placeholder = "Define color code",
    className,
}: {
    value: string;
    onValueChange: (value: string) => void;
    placeholder?: string;
    className?: string;
}) {
    const pickerValue = colorPickerValue(value);

    return (
        <div className={cn("relative", className)}>
            <StyledInput
                placeholder={placeholder}

                value={value}
                onChange={(event) => onValueChange(event.target.value)}
                className="pr-14 bg-section-input-field"
            />
            <label
                className="absolute right-3 top-1/2 flex h-7 w-7 -translate-y-1/2 cursor-pointer items-center justify-center text-[#9D9D9D] transition hover:text-primary"
                title="Pick color"
            >
                <Pipette className="h-5 w-5" />
                <input
                    type="color"
                    value={pickerValue}
                    aria-label="Pick color"
                    className="sr-only"
                    onChange={(event) => onValueChange(event.target.value.toUpperCase())}
                />
            </label>
        </div>
    );
}

export function StyledTextarea(props: ComponentProps<typeof Textarea>) {
    return (
        <Textarea
            {...props}
            className={cn(
                "min-h-24 rounded-xl border-none bg-input-field px-4 py-3 text-sm shadow-none focus-visible:ring-2 focus-visible:ring-primary/20",
                props.className,
            )}
        />
    );
}

export function StyledSelect({
    value,
    onValueChange,
    placeholder,
    options,
    className,
    getOptionLabel,
    clearable = true,
}: {
    value: string;
    onValueChange: (value: string) => void;
    placeholder: string;
    options: readonly string[];
    className?: string;
    getOptionLabel?: (value: string) => string;
    clearable?: boolean;
}) {
    const [open, setOpen] = useState(false);
    const canClear = clearable && Boolean(value);

    return (
        <div className="relative w-full">
            <Select
                open={open}
                onOpenChange={setOpen}
                value={value}
                onValueChange={onValueChange}
            >
                <SelectTrigger className={cn("h-12 w-full rounded-xl border-none cursor-pointer bg-input-field px-4 py-6 text-left text-sm shadow-none focus-visible:ring-2 focus-visible:ring-primary/20", canClear && "pr-16", className)}>
                    <SelectValue placeholder={placeholder} />
                </SelectTrigger>
                <SelectContent>
                    {options.map((option) => (
                        <SelectItem
                            key={option}
                            value={option}
                            onSelect={(event) => {
                                if (clearable && option === value) {
                                    event.preventDefault();
                                    onValueChange("");
                                    setOpen(false);
                                }
                            }}
                        >
                            {getOptionLabel ? getOptionLabel(option) : option}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>
            {canClear ? (
                <button
                    type="button"
                    aria-label={`Clear ${placeholder}`}
                    className="absolute right-9 top-1/2 z-10 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
                    onPointerDown={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                    }}
                    onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        onValueChange("");
                        setOpen(false);
                    }}
                >
                    <X className="h-4 w-4" />
                </button>
            ) : null}
        </div>
    );
}

export function CheckboxList({
    options,
    values,
    onToggle,
    className,
}: {
    options: string[];
    values: string[];
    onToggle: (value: string) => void;
    className?: string;
}) {
    return (
        <div className={cn("space-y-3", className)}>
            {options.map((option) => {
                const checked = values.includes(option);
                return (
                    <Label key={option} className="flex items-center gap-3 text-base text-slate-700">
                        <Checkbox checked={checked} onCheckedChange={() => onToggle(option)} />
                        <span>{option}</span>
                    </Label>
                );
            })}
        </div>
    );
}

export function FileUploadField({
    label,
    acceptedFormats,
    item,
    onChange,
    onRemove,
    required,
    uploadLabel = "Upload file",
    className,
}: SingleUploadProps) {
    const inputRef = useRef<HTMLInputElement | null>(null);
    const inputId = useId();

    return (
        <div className={cn("space-y-3", className)}>
            <div>
                <p className="text-base font-medium text-[#121212]">
                    {label}
                    {required ? <span className="ml-1 text-red-500">*</span> : null}
                </p>
                <p className="text-sm text-slate-500">Formats accepted: {acceptedFormats}</p>
            </div>
            <input
                id={inputId}
                ref={inputRef}
                type="file"
                className="hidden"
                accept={acceptedFormatsToAccept(acceptedFormats)}
                onChange={(event) => {
                    onChange(event.target.files);
                    event.currentTarget.value = "";
                }}
            />
            <div className="flex flex-wrap gap-4">
                <Button
                    type="button"
                    onClick={() => inputRef.current?.click()}
                    className="flex h-20 w-60 flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#E5E4E4] bg-[#FFFFFF] text-sm text-[#121212] transition hover:border-primary/40 hover:bg-slate-50"
                >
                    <Upload className="mb-2 h-4 w-4" />
                    <span className="text-sm">{uploadLabel}</span>
                </Button>
                {item ? <UploadedFileCard item={item} onRemove={onRemove} /> : null}
            </div>
        </div>
    );
}

export function FileUploadCollection({
    label,
    acceptedFormats,
    items,
    onAdd,
    onRemove,
    activeItemId,
    onSelect,
    multiple = true,
    tags,
    className,
    bgColor,
    required
}: UploadCollectionProps) {
    const inputRef = useRef<HTMLInputElement | null>(null);
    const inputId = useId();

    return (
        <div className={cn("space-y-3", className)}>
            <div>
                <p className="text-base font-medium text-black">{label}
                    {required ? <span className="ml-1 text-red-500">*</span> : null}
                </p>
                <p className="text-sm text-slate-500">Formats accepted: {acceptedFormats}</p>
            </div>
            <input
                id={inputId}
                ref={inputRef}
                type="file"
                className="hidden"
                accept={acceptedFormatsToAccept(acceptedFormats)}
                multiple={multiple}
                onChange={(event) => {
                    onAdd(event.target.files);
                    event.currentTarget.value = "";
                }}
            />
            <div className="flex flex-wrap gap-4">
                <Button
                    type="button"
                    onClick={() => inputRef.current?.click()}
                    className={cn(`flex h-20 w-60 flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#E5E4E4] ${bgColor || 'bg-[#F6F6F6]'} text-sm text-slate-600 transition hover:border-primary/40 hover:bg-slate-50`)}
                >
                    <Upload className="mb-2 h-4 w-4" />
                    Upload
                    {tags?.length ? (
                        <div className="mt-3 flex flex-wrap justify-center gap-1">
                            {tags.map((tag) => (
                                <span
                                    key={tag}
                                    className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-500"
                                >
                                    {tag}
                                </span>
                            ))}
                        </div>
                    ) : null}
                </Button>
                {items.map((item) => (
                    <UploadedFileCard
                        key={item.id}
                        item={item}
                        isActive={item.id === activeItemId}
                        onSelect={onSelect ? () => onSelect(item.id) : undefined}
                        onRemove={() => onRemove(item.id)}
                    />
                ))}
            </div>
        </div>
    );
}

export function FontPickerField({
    label,
    required,
    value,
    placeholder,
    options,
    onValueChange,
    acceptedFormats,
    uploadedItems,
    onUpload,
    onRemoveUpload,
    isLoading,
    error,
    className,
}: FontPickerFieldProps) {
    const inputRef = useRef<HTMLInputElement | null>(null);
    const inputId = useId();
    const listId = useId();
    const [open, setOpen] = useState(false);
    const selectedOption = options.find((option) => option.family === value);

    return (
        <div className={cn("space-y-3", className)}>
            <div className="flex items-center justify-between gap-4">
                <p className="text-base font-medium text-[#121212]">
                    {label}
                    {required ? <span className="ml-1 text-red-500">*</span> : null}
                </p>
                <button
                    type="button"
                    onClick={() => inputRef.current?.click()}
                    className="text-base font-medium text-[#121212] underline underline-offset-4 transition hover:text-primary"
                >
                    Upload
                </button>
            </div>

            <input
                id={inputId}
                ref={inputRef}
                type="file"
                className="hidden"
                accept={acceptedFormatsToAccept(acceptedFormats)}
                multiple
                onChange={(event) => {
                    onUpload(event.target.files);
                    event.currentTarget.value = "";
                }}
            />

            <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                    <Button
                        type="button"
                        role="combobox"
                        aria-expanded={open}
                        aria-controls={listId}
                        className="flex h-12 w-full items-center justify-between rounded-xl bg-white px-5 text-left shadow-none outline-none transition focus-visible:ring-2 focus-visible:ring-primary/20"
                    >
                        <span className={cn("truncate text-base", value ? "text-[#2C2C2C]" : "text-[#A1A1AA]")}>
                            {value || placeholder}
                        </span>
                        {isLoading ? (
                            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
                        ) : (
                            <ChevronDown className="h-5 w-5 text-slate-500" />
                        )}
                    </Button>
                </PopoverTrigger>
                <PopoverContent
                    align="start"
                    className="w-[var(--radix-popover-trigger-width)] rounded-[22px] border border-[#E5E7EB] bg-white p-0 shadow-[0_18px_48px_-20px_rgba(15,23,42,0.35)]"
                >
                    <Command className="rounded-md">
                        <CommandInput placeholder="Search Google Fonts" />
                        {error ? (
                            <div className="px-4 py-6 text-sm text-amber-700">
                                {error}
                            </div>
                        ) : isLoading ? (
                            <div className="flex items-center gap-2 px-4 py-6 text-sm text-slate-500">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Loading Google Fonts...
                            </div>
                        ) : (
                            <CommandList id={listId} className="max-h-72">
                                <CommandEmpty>No matching fonts found.</CommandEmpty>
                                <CommandGroup>
                                    {options.map((option) => (
                                        <CommandItem
                                            key={option.family}
                                            value={option.family}
                                            onSelect={() => {
                                                onValueChange(option.family);
                                                setOpen(false);
                                            }}
                                            className="flex items-start gap-3 px-3 py-3"
                                        >
                                            <Check
                                                className={cn(
                                                    "mt-0.5 h-4 w-4 text-primary transition-opacity",
                                                    value === option.family ? "opacity-100" : "opacity-0",
                                                )}
                                            />
                                            <div className="min-w-0">
                                                <p className="truncate text-sm font-medium text-[#2C2C2C]">
                                                    {option.family}
                                                </p>
                                                <p className="truncate text-xs capitalize text-slate-500">
                                                    {option.category || "google font"}
                                                    {option.variants?.length
                                                        ? ` • ${option.variants.length} style${option.variants.length > 1 ? "s" : ""}`
                                                        : ""}
                                                </p>
                                            </div>
                                        </CommandItem>
                                    ))}
                                </CommandGroup>
                            </CommandList>
                        )}
                    </Command>
                </PopoverContent>
            </Popover>

            <p className="text-sm text-slate-500">
                Search Google Fonts or upload custom font files. Accepted formats: {acceptedFormats}.
            </p>

            {selectedOption ? (
                <p className="text-sm capitalize text-slate-500">
                    Selected Google Font: {selectedOption.family}
                    {selectedOption.category ? ` (${selectedOption.category})` : ""}
                </p>
            ) : null}

            {uploadedItems.length ? (
                <div className="flex flex-wrap gap-4 pt-1">
                    {uploadedItems.map((item) => (
                        <UploadedFileCard key={item.id} item={item} onRemove={() => onRemoveUpload(item.id)} />
                    ))}
                </div>
            ) : null}
        </div>
    );
}

export function AdditionalColorRow({
    name,
    hex,
    onNameChange,
    onHexChange,
    canRemove,
    onRemove,
}: {
    name: string;
    hex: string;
    onNameChange: (value: string) => void;
    onHexChange: (value: string) => void;
    canRemove: boolean;
    onRemove: () => void;
}) {
    return (
        <div className="flex items-center gap-2 md:w-[calc(100%+2.25rem)]">
            <div className="grid flex-1 gap-3 md:grid-cols-2">
                <StyledInput placeholder="Define color name" value={name} onChange={(e) => onNameChange(e.target.value)}
                    className="bg-section-input-field"
                />
                <ColorHexInput value={hex} onValueChange={onHexChange} />
            </div>
            {canRemove ? (
                <Button
                    type="button"
                    variant="ghost"
                    size="icon-sm"
                    onClick={onRemove}
                    className="active:translate-y-0"
                    aria-label="Remove additional color"
                >
                    <X className="h-4 w-4" />
                </Button>
            ) : (
                <span className="size-7 shrink-0" />
            )}
        </div>
    );
}

export function AddMoreButton({
    onClick,
    children = "Add more",
}: {
    onClick: () => void;
    children?: ReactNode;
}) {
    return (
        <button type="button" onClick={onClick} className="inline-flex items-center gap-2 text-sm font-medium text-primary">
            <Plus className="h-4 w-4" />
            {children}
        </button>
    );
}

function UploadedFileCard({
    item,
    onRemove,
    isActive = false,
    onSelect,
}: {
    item: BrandUploadItem;
    onRemove: () => void;
    isActive?: boolean;
    onSelect?: () => void;
}) {
    const [isPreviewOpen, setIsPreviewOpen] = useState(false);
    const previewSource = item.previewUrl || item.assetUrl;
    const isImagePreview =
        Boolean(previewSource) &&
        (
            String(item.mimeType || "").startsWith("image/") ||
            /\.(png|jpe?g|webp|svg)$/i.test(String(previewSource || ""))
        );
    const normalizedState = (item.lifecycleState || "").toLowerCase();
    const isReadyToUpload = normalizedState === "selected";
    const isQueued = ["uploaded", "queued"].includes(normalizedState);
    const isProcessing = ["uploading", "processing", "analyzing"].includes(normalizedState);
    const isReady = ["indexed", "complete", "ready"].includes(normalizedState);
    const isFailed = normalizedState === "failed";
    const statusLabel =
        normalizedState === "selected"
            ? "Ready"
            : normalizedState === "uploading"
                ? "Uploading"
                : normalizedState === "uploaded" || normalizedState === "queued"
                    ? "Queued"
                    : normalizedState === "analyzing"
                        ? "Analyzing"
                        : normalizedState === "processing"
                            ? "Processing"
                            : normalizedState === "indexed" || normalizedState === "complete" || normalizedState === "ready"
                                ? "Synced"
                                : normalizedState === "failed"
                                    ? "Failed"
                                    : item.lifecycleState;
    return (
        <>
            <div
                role={onSelect ? "button" : undefined}
                tabIndex={onSelect ? 0 : undefined}
                aria-pressed={onSelect ? isActive : undefined}
                onClick={onSelect}
                onKeyDown={(event) => {
                    if (!onSelect || (event.key !== "Enter" && event.key !== " ")) {
                        return;
                    }
                    event.preventDefault();
                    onSelect();
                }}
                className={cn(
                    "w-40 rounded-xl border bg-white p-3 shadow-[0_10px_20px_-18px_rgba(15,23,42,0.45)] transition",
                    onSelect ? "cursor-pointer hover:border-primary/50" : "",
                    isActive ? "border-primary ring-2 ring-primary/15" : "border-slate-200",
                )}
            >
                <div className="flex items-start justify-between gap-2">
                    <Button
                        type="button"
                        onClick={(event) => {
                            event.stopPropagation();
                            if (isImagePreview) {
                                setIsPreviewOpen(true);
                            }
                        }}
                        disabled={!isImagePreview}
                        className={cn(
                            "flex h-7 w-8 items-center justify-center overflow-hidden rounded-md bg-primary/8 text-sky-500 transition",
                            isImagePreview ? "hover:bg-sky-100" : "cursor-default",
                        )}
                    >
                        {isImagePreview ? <Eye className="h-4 w-4" /> : item.assetUrl ? <ImagePlus className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                    </Button>
                    <Button
                        variant={"ghost"}
                        type="button"
                        className="w-6 h-6 text-slate-400 transition bg-none hover:bg-none p-0"
                        onClick={(event) => {
                            event.stopPropagation();
                            onRemove();
                        }}
                    >
                        <Image src="/brandSpaces/remove.svg" alt="Remove file" width={16} height={16} className="h-4.5 w-4.5" />
                    </Button>
                </div>
                <p className="mt-3 line-clamp-2 text-xs font-medium text-slate-700">{item.name}</p>
                {statusLabel ? (
                    <div className="mt-2 flex items-center gap-1.5 text-[11px] uppercase tracking-[0.18em]">
                        {isReadyToUpload ? <FileText className="h-3 w-3 text-slate-500" /> : null}
                        {isProcessing ? <Loader2 className="h-3 w-3 animate-spin text-primary" /> : null}
                        {isQueued ? <Loader2 className="h-3 w-3 text-amber-500" /> : null}
                        {isReady ? <CheckCircle2 className="h-3 w-3 text-emerald-600" /> : null}
                        {isFailed ? <AlertCircle className="h-3 w-3 text-red-500" /> : null}
                        <span className={`text-[10px] ${isFailed ? "text-red-500" : isReady ? "text-emerald-600" : isQueued ? "text-amber-600" : isReadyToUpload ? "text-slate-500" : "text-slate-400"}`}>
                            {statusLabel}
                        </span>
                    </div>
                ) : null}
                {item.pageCount ? <p className="mt-1 text-[11px] text-slate-500">{item.pageCount} OCR page{item.pageCount > 1 ? "s" : ""}</p> : null}
                {item.processingError ? <p className="mt-1 text-[11px] text-red-500">{item.processingError}</p> : null}
                {item.tags?.length ? (
                    <div className="mt-2 flex flex-wrap gap-1">
                        {item.tags.map((tag) => (
                            <span
                                key={tag}
                                className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-500"
                            >
                                {tag}
                            </span>
                        ))}
                    </div>
                ) : null}
            </div>
            <Dialog open={isPreviewOpen} onOpenChange={setIsPreviewOpen}>
                <DialogContent className="max-w-4xl border-slate-200 bg-white p-4">
                    <DialogHeader>
                        <DialogTitle className="truncate pr-8 text-base text-slate-900">{item.name}</DialogTitle>
                    </DialogHeader>
                    {previewSource ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={previewSource} alt={item.name} className="max-h-[75vh] w-full rounded-xl object-contain" />
                    ) : null}
                </DialogContent>
            </Dialog>
        </>
    );
}

function acceptedFormatsToAccept(value: string) {
    return value
        .split(/[,\s/]+/)
        .map((item) => item.trim().toLowerCase())
        .filter(Boolean)
        .map((item) => {
            if (item.startsWith(".")) {
                return item;
            }
            if (item.includes("/")) {
                return item;
            }
            return `.${item}`;
        })
        .join(",");
}
