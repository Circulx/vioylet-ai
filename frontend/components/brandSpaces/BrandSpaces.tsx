"use client";

import Image from "next/image";
import Link from "next/link";
import { Archive, Edit2, Edit3Icon, MoreVertical, NotebookPen, Trash2 } from "lucide-react";
import { StatusChip } from "@/components/common/DesignPrimitives";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { BrandResponse } from "@/lib/api/contracts";
import { buildBrandEditHref, buildBrandWorkspaceHref } from "@/lib/brand-routing";
import { resolveBrandLogoUrl } from "@/lib/brand-assets";
import { Button } from "../ui/button";

type BrandSpaceListItem = BrandResponse & {
  logo?: string;
};

type BrandSpacesProps = {
  items: BrandSpaceListItem[];
  onPublish?: (item: BrandSpaceListItem) => void;
  onUnpublish?: (item: BrandSpaceListItem) => void;
  onArchive?: (item: BrandSpaceListItem) => void;
  onRestore?: (item: BrandSpaceListItem) => void;
  onDelete?: (item: BrandSpaceListItem) => void;
};

export default function BrandSpaces({
  items,
  onPublish,
  onUnpublish,
  onArchive,
  onRestore,
  onDelete,
}: BrandSpacesProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {items.map((item) => {
        const logoUrl = resolveBrandLogoUrl(item);
        const lifecycleState = "lifecycle_state" in item ? item.lifecycle_state : undefined;
        const helperLabel =
          lifecycleState === "archived"
            ? "Archived"
            : lifecycleState === "active"
              ? "Active"
              : lifecycleState === "draft"
                ? "Draft"
                : null;
        return (
          <div
            key={item.id}
            className="group relative flex min-h-30 flex-col justify-between border border-[#C5C5C5] p-4 transition hover:border-primary/30 hover:shadow-[0_20px_32px_-24px_rgba(60,47,143,0.35)]"
          >
            <div className="flex items-start justify-between gap-3">
              {helperLabel ? <StatusChip tone={helperLabel === "Active" ? "success" : "neutral"}>{helperLabel}</StatusChip> : <span />}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                  variant={"ghost"}
                    aria-label={`${item.name} actions`}
                    className="rounded-full p-1 text-slate-300 transition"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-44">
                  {lifecycleState === "draft" ? (
                    <DropdownMenuItem onClick={() => onPublish?.(item)}>
                      Make Active
                    </DropdownMenuItem>
                  ) : null}
                  {lifecycleState === "active" ? (
                    <DropdownMenuItem onClick={() => onUnpublish?.(item)}>
                        <NotebookPen />
                      Move to Draft
                    </DropdownMenuItem>
                  ) : null}
                  {lifecycleState !== "archived" ? (
                    <DropdownMenuItem onClick={() => onArchive?.(item)}>
                        <Archive />
                      Archive
                    </DropdownMenuItem>
                  ) : null}
                  {lifecycleState === "archived" ? (
                    <DropdownMenuItem onClick={() => onRestore?.(item)}>
                      Restore
                    </DropdownMenuItem>
                  ) : null}
                  <DropdownMenuItem asChild>
                    <Link href={buildBrandEditHref(item)}>
                        <Edit3Icon />
                      Edit
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuItem variant="destructive" onClick={() => onDelete?.(item)}>
                  <Trash2 />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <Link href={buildBrandWorkspaceHref(item)} className="block">
              <div className="flex min-h-[56px] items-center justify-center py-3">
                {logoUrl ? (
                  <div className="relative h-24 w-48 overflow-hidden">
                    <Image
                      src={logoUrl}
                      alt={item.name}
                      fill
                      unoptimized
                      className="scale-[1.65] object-contain"
                      sizes="192px"
                    />
                  </div>
                ) : (
                  <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#F3F4F8] text-2xl font-bold text-primary">
                    {item.name.slice(0, 1)}
                  </div>
                )}
              </div>

              <div className="space-y-1 border-t border-[#F1F2F6] pt-4">
                <p className="text-sm font-medium text-[#2F3342]">{item.name}</p>
                {/* <p className="text-sm text-[#7A7F8F]">Open workspace</p> */}
              </div>
            </Link>
          </div>
        );
      })}
    </div>
  );
}
