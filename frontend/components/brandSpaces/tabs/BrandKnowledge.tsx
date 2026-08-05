import { type ChangeEvent, type KeyboardEvent, useRef, useState } from "react";
import { FileText, Trash2, UploadCloud, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  createBrandUploadItem,
  type BrandTabProps,
  type BrandUploadItem,
  updateBrandFormSection,
} from "@/types/brand-space.types";
import { FormSection } from "./FormFields";
import Image from "next/image";

const KNOWLEDGE_UPLOAD_FORMATS = "PDF, JPG, PNG, DOCX";
const MAX_FILE_SIZE_MB = 25;

type BrandKnowledgeKey = "templateFiles" | "otherDocuments";

type PendingUpload = {
  item: BrandUploadItem;
  tagDraft: string;
};

type KnowledgeUploadFieldProps = {
  label: string;
  items: BrandUploadItem[];
  onAddItems: (items: BrandUploadItem[]) => void;
  onRemove: (itemId: string) => void;
};

const BrandKnowledge = ({ form, setForm, onRemoveUpload }: BrandTabProps) => {
  const updateField = <TKey extends keyof typeof form.brandKnowledge>(
    key: TKey,
    value: (typeof form.brandKnowledge)[TKey],
  ) => updateBrandFormSection(setForm, "brandKnowledge", key, value);

  const addUploads = (key: BrandKnowledgeKey, items: BrandUploadItem[]) => {
    if (!items.length) {
      return;
    }
    updateField(key, [...form.brandKnowledge[key], ...items]);
  };

  const removeUpload = (key: BrandKnowledgeKey, itemId: string) => {
    if (onRemoveUpload) {
      void onRemoveUpload(itemId);
      return;
    }
    updateField(
      key,
      form.brandKnowledge[key].filter((item) => item.id !== itemId),
    );
  };

  return (
    <FormSection title="Documentation">
      <KnowledgeUploadField
        label="Template"
        items={form.brandKnowledge.templateFiles}
        onAddItems={(items) => addUploads("templateFiles", items)}
        onRemove={(itemId) => removeUpload("templateFiles", itemId)}
      />

      <KnowledgeUploadField
        label="Other documentation"
        items={form.brandKnowledge.otherDocuments}
        onAddItems={(items) => addUploads("otherDocuments", items)}
        onRemove={(itemId) => removeUpload("otherDocuments", itemId)}
      />
    </FormSection>
  );
};

function KnowledgeUploadField({ label, items, onAddItems, onRemove }: KnowledgeUploadFieldProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([]);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const addPendingFiles = (files: FileList | null) => {
    if (!files?.length) {
      return;
    }

    const nextItems = Array.from(files)
      .filter((file) => file.size <= MAX_FILE_SIZE_MB * 1024 * 1024)
      .map((file) => ({
        item: createBrandUploadItem(file),
        tagDraft: "",
      }));

    if (!nextItems.length) {
      return;
    }

    setPendingUploads((current) => [...current, ...nextItems]);
  };

  const updatePendingItem = (itemId: string, updater: (upload: PendingUpload) => PendingUpload) => {
    setPendingUploads((current) => current.map((upload) => (upload.item.id === itemId ? updater(upload) : upload)));
  };

  const commitTags = (itemId: string, value?: string) => {
    updatePendingItem(itemId, (upload) => {
      const source = value ?? upload.tagDraft;
      const nextTags = parseTags(source);
      if (!nextTags.length) {
        return { ...upload, tagDraft: "" };
      }
      return {
        item: {
          ...upload.item,
          tags: uniqueTags([...(upload.item.tags || []), ...nextTags]),
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
    const completedTags = parseTags(parts.join(","));
    updatePendingItem(itemId, (upload) => ({
      item: {
        ...upload.item,
        tags: uniqueTags([...(upload.item.tags || []), ...completedTags]),
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

  const removePendingFile = (itemId: string) => {
    setPendingUploads((current) => current.filter((upload) => upload.item.id !== itemId));
  };

  const handleUploadAll = () => {
    const finalizedItems = pendingUploads.map((upload) => ({
      ...upload.item,
      tags: uniqueTags([...(upload.item.tags || []), ...parseTags(upload.tagDraft)]),
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
        <p className="text-base font-medium text-black">{label}</p>
        <p className="text-sm text-slate-500">Formats accepted: {KNOWLEDGE_UPLOAD_FORMATS}</p>
      </div>

      <div className="flex flex-wrap gap-4">
        <Button
          type="button"
          onClick={() => setIsOpen(true)}
          className="flex h-20 w-60 flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#E5E4E4] bg-[#F6F6F6] text-sm text-slate-600 transition hover:border-primary/40 hover:bg-slate-50"
        >
          <UploadCloud className="mb-2 h-4 w-4" />
          Upload
        </Button>
        {items.map((item) => (
          <KnowledgeUploadedFileCard key={item.id} item={item} onRemove={() => onRemove(item.id)} />
        ))}
      </div>

      <Dialog open={isOpen} onOpenChange={handleOpenChange}>
        <DialogContent className="max-h-[90vh] w-full max-w-5xl overflow-hidden border-none bg-white p-0 shadow-xl" showCloseButton>
          <DialogTitle className="sr-only">Upload {label} files</DialogTitle>
          <div className="mx-auto my-8 flex max-h-[calc(90vh-4rem)] w-[88%] flex-col rounded-sm bg-[#F4F4F4] px-8 py-6">
            <div className="mx-auto flex min-h-0 w-full max-w-[400px] flex-col gap-7">
              <h3 className="text-base font-bold text-[#121212]">Upload File:</h3>

              <Button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="flex h-36 w-full flex-col items-center justify-center rounded-xl border-2 border-dashed border-[#D8E2EC] bg-white text-sm text-[#8191A7] transition hover:border-[#56BBD1]"
              >
                {/* <span className="mb-5 flex h-16 w-16 items-center justify-center rounded-full bg-[#EAF6F8] text-[#56BBD1]">
                  <UploadCloud className="h-14 w-14" />
                </span> */}
                <span className="mb-5 bg-[#52B2CF21] p-3 rounded-4xl">
                <Image src="/brandSpaces/upload_cloud.svg" alt="Upload file icon" width={33} height={33} className="" />
                </span>
                {KNOWLEDGE_UPLOAD_FORMATS} (Max {MAX_FILE_SIZE_MB}MB per file)
              </Button>
              <input
                ref={inputRef}
                type="file"
                multiple
                className="hidden"
                accept={acceptedFormatsToAccept(KNOWLEDGE_UPLOAD_FORMATS)}
                onChange={(event: ChangeEvent<HTMLInputElement>) => {
                  addPendingFiles(event.target.files);
                  event.currentTarget.value = "";
                }}
              />

              <div className="min-h-0 flex-1 space-y-7 overflow-y-auto pr-2">
                {pendingUploads.map((upload) => (
                  <PendingUploadCard
                    key={upload.item.id}
                    upload={upload}
                    onDelete={() => removePendingFile(upload.item.id)}
                    onTagChange={(value) => handleTagInputChange(upload.item.id, value)}
                    onTagKeyDown={(event) => handleTagKeyDown(event, upload.item.id)}
                    onTagBlur={() => commitTags(upload.item.id)}
                    onRemoveTag={(tag) => removePendingTag(upload.item.id, tag)}
                  />
                ))}
              </div>

              {pendingUploads.length ? (
                <div className="shrink-0 flex justify-center pt-1">
                  <Button
                    type="button"
                    onClick={handleUploadAll}
                    className="h-14 rounded-none bg-primary px-10 text-lg font-medium text-white hover:bg-[#36237E]"
                  >
                    Upload All
                    <Image src="/brandSpaces/document-upload.svg" alt="Upload file icon" width={20} height={20} className="ml-2 text-white" />
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

function PendingUploadCard({
  upload,
  onDelete,
  onTagChange,
  onTagKeyDown,
  onTagBlur,
  onRemoveTag,
}: {
  upload: PendingUpload;
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

function KnowledgeUploadedFileCard({ item, onRemove }: { item: BrandUploadItem; onRemove: () => void }) {
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

function parseTags(value: string) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function uniqueTags(tags: string[]) {
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

export default BrandKnowledge;
