"use client";

import { useState } from "react";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";

type Props = {
  caption: string;
  platform?: string;
};

async function copyCaption(text: string) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

export default function PostCaptionBlock({ caption, platform }: Props) {
  const [copied, setCopied] = useState(false);

  if (!caption.trim()) {
    return null;
  }

  const platformLabel =
    platform === "instagram"
      ? "Instagram"
      : platform === "linkedin"
        ? "LinkedIn"
        : platform === "x" || platform === "twitter"
          ? "X"
          : "Social";

  const handleCopy = async () => {
    await copyCaption(caption);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border border-slate-200 bg-white/90 p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] font-bold uppercase tracking-wide text-slate-600">
          Post caption · {platformLabel}
        </p>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => void handleCopy()}
          className="h-7 gap-1.5 px-2 text-[11px] text-slate-600"
        >
          <Copy className="h-3.5 w-3.5" />
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">{caption}</p>
    </div>
  );
}
