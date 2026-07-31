"use client";

import { apiOrigin } from "@/lib/env";
import Image from "next/image";
import React, { useEffect, useMemo, useRef, useState } from "react";
import { Label } from "../ui/label";

const MAX_SIZE = 2 * 1024 * 1024;
const ALLOWED_TYPES = ["image/png", "image/jpeg"];

function resolvePreview(value?: File | string | null) {
  if (!value) {
    return null;
  }
  if (typeof value === "string") {
    if (value.startsWith("blob:") || value.startsWith("data:") || value.startsWith("http")) {
      return value;
    }
    return `${apiOrigin}/storage/${value}`;
  }
  return URL.createObjectURL(value);
}

const TenantLogoUpload = ({
  value,
  onChange,
}: {
  value?: File | string | null;
  onChange: (logo: File | string) => void;
}) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const preview = useMemo(() => resolvePreview(value), [value]);

  useEffect(() => {
    return () => {
      if (preview?.startsWith("blob:")) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  const validateFile = (file: File) => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Only PNG or JPEG allowed");
      return false;
    }

    if (file.size > MAX_SIZE) {
      setError("File size should be less than 2MB");
      return false;
    }

    return true;
  };

  const handleFile = (file: File) => {
    if (!validateFile(file)) {
      return;
    }

    onChange(file);
    setError(null);
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (selected) {
      handleFile(selected);
    }
  };

  const handleRemove = () => {
    onChange("");
    setError(null);
    setDragActive(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="w-full flex-1 space-y-3">
      <Label className="flex flex-col items-start gap-1 text-base font-medium leading-6 text-[#2F3342]">
        <span className="text-base">Tenant logo</span>
        <span className="text-base font-normal text-[#4B5563]">Custom branding in widget</span>
      </Label>

      <div className="relative w-fit">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(event) => {
            event.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragActive(false);
            const droppedFile = event.dataTransfer.files?.[0];
            if (droppedFile) {
              handleFile(droppedFile);
            }
          }}
          className={`flex h-[77px] w-[191px] flex-col items-center justify-center rounded-[10px] border-2 hover:border-4 cursor-pointer border-dashed text-center transition ${
            dragActive ? "border-primary bg-primary/5" : "border-primary/80 bg-[#F6F6F6]"
          }`}
        >
          {preview ? (
            <Image
              src={preview}
              alt="logo preview"
              width={160}
              height={64}
              unoptimized
              className="h-14 w-auto object-contain"
            />
          ) : (
            <>
              <Image
                src="/actions_icons/document-upload.svg"
                alt="upload placeholder"
                width={32}
                height={32}
                className="mb-1 h-5 w-5"
              />
              <span className="text-base font-medium leading-[22px] text-[#2F3342] underline">Upload logo</span>
            </>
          )}
        </button>
        {preview ? (
          <button
            type="button"
            onClick={handleRemove}
            className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center bg-none p-0 text-slate-400 transition hover:bg-none"
            aria-label="Remove tenant logo"
          >
            <Image
              src="/brandSpaces/remove.svg"
              alt="Remove file"
              width={16}
              height={16}
              className="h-4.5 w-4.5"
            />
          </button>
        ) : null}
      </div>

      {error ? <p className="text-sm text-red-500">{error}</p> : null}

      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept="image/png, image/jpeg"
        onChange={handleFileChange}
      />
    </div>
  );
};

export default TenantLogoUpload;
