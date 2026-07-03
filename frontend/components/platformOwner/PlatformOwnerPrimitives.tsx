"use client";

import type { ReactNode } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "../ui/button";
import Image from "next/image";
import Link from "next/link";

export function PlatformPageTitle({
    title,
    action,
    children,
}: {
    title: string;
    action?: ReactNode;
    children?: ReactNode;
}) {
    return (
        <div className="space-y-6">
            <div className="flex items-start justify-between gap-4">
                <h1 className="font-dmSans text-[32px] font-bold leading-none text-primary">{title}</h1>
                {action}
            </div>
            {children}
        </div>
    );
}

export function PlatformTabSwitcher({
    tabs,
    active,
    onChange,
}: {
    tabs: Array<{ id: string; label: string }>;
    active: string;
    onChange: (tab: string) => void;
}) {
    return (
        <div className="flex flex-wrap items-center gap-3">
            {tabs.map((tab) => (
                <Button
                    key={tab.id}
                    type="button"
                    onClick={() => onChange(tab.id)}
                    className={cn(
                        "h-12 min-w-[161px] rounded-[10px] border border-[#D4D8E5] bg-white px-5 text-[15px] font-medium text-[#2F3342] transition",
                        active === tab.id ? "bg-[#CDCDCD]/22 shadow-[inset_0_0_0_1px_rgba(60,47,143,0.14)]" : "hover:bg-[#FAFAFD]",
                    )}
                >
                    {tab.label}
                </Button>
            ))}
        </div>
    );
}

export function UserPlatformTabSwitcher({
    tabs,
    active,
    className,
    onChange,
}: {
    tabs: Array<{ id: string; label: string }>;
    active: string;
    className?: string;
    onChange: (tab: string) => void;
}) {
    return (
        <div className={cn("flex flex-wrap items-center border-b", className)}>
            {tabs.map((tab) => (
                <Button
                    key={tab.id}
                    variant={"ghost"}
                    type="button"
                    onClick={() => onChange(tab.id)}
                    className={cn(
                        "h-12 min-w-24 px-4 rounded-none bg-white px-5 text-[15px] font-medium text-[#2F3342] transition",
                        active === tab.id ? "bg-[#EFEFEF70]" : "hover:bg-[#FAFAFD]",
                    )}
                >
                    {tab.label}
                </Button>
            ))}
        </div>
    );
}

export function DatePill({ label }: { label: string }) {
    return (
        <div className="inline-flex h-10 items-center gap-2 rounded-[10px] border border-[#D5D8E8] bg-white px-3 text-sm font-medium text-[#6B7280]">
            <CalendarDays className="h-3.5 w-3.5" />
            <span>{label}</span>
        </div>
    );
}

export function SectionCard({
    title,
    description,
    toolbar,
    children,
    className,
    titleClassName,
    externalLink,
    externalLinkText,
}: {
    title?: string;
    description?: string;
    toolbar?: ReactNode;
    children: ReactNode;
    className?: string;
    titleClassName?: string;
    externalLink?: string;
    externalLinkText?: string;
}) {
    return (
        <div className={cn("border border-[#E4E7EC] bg-white p-3", className)}>
            <div className={cn(
                "flex flex-col gap-2",
                toolbar ? "sm:flex-row sm:items-start sm:justify-between" : "items-start",
            )}>
                <div className="min-w-0 flex flex-col items-start justify-center">
                    <h2 className={cn`text-xl font-semibold text-black ${!toolbar ? 'py-4' : ''}`}>{title}</h2>
                    {description ? (
                        <p className="text-sm text-[#6B7280]">
                            {description}
                            {externalLink && externalLinkText ? (
                                <Link href={externalLink} target="_self" rel="noopener noreferrer" className="ml-1 text-sm text-primary underline">
                                    {externalLinkText}
                                </Link>
                            ) : null}
                        </p>
                    ) : null}
                </div>
                {toolbar ? <div className="shrink-0 pb-4">{toolbar}</div> : null}
            </div>
            {children}
        </div>
    );
}

export function OwnerSectionCard({
    title,
    description,
    toolbar,
    children,
    className,
    titleClassName,
    externalLink,
    externalLinkText,
}: {
    title?: string;
    description?: string;
    toolbar?: ReactNode;
    children: ReactNode;
    className?: string;
    titleClassName?: string;
    externalLink?: string;
    externalLinkText?: string;
}) {
    return (
        <div className={cn("border border-[#E4E7EC] bg-white p-3", className)}>
            <div className={cn(
                "flex flex-col gap-2",
                toolbar ? "sm:flex-row sm:items-start sm:justify-between" : "items-start",
            )}>
                <div className="min-w-0 flex flex-col items-start justify-center">
                    <h2 className={cn`text-base font-semibold text-black`}>{title}</h2>
                    {description ? (
                        <p className="text-sm text-[#6B7280]">
                            {description}
                            {externalLink && externalLinkText ? (
                                <Link href={externalLink} target="_self" rel="noopener noreferrer" className="ml-1 text-sm text-primary underline">
                                    {externalLinkText}
                                </Link>
                            ) : null}
                        </p>
                    ) : null}
                </div>
                {toolbar ? <div className="shrink-0 pb-4">{toolbar}</div> : null}
            </div>
            {children}
        </div>
    );
}


export function MetricTile({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-xs border border-[#ECEEF5] bg-white px-5 py-4">
            <p className="text-sm text-[#6B7280]">{label}</p>
            <p className="mt-3 text-xl font-semibold leading-none text-[#2F3342]">{value}</p>
        </div>
    );
}

export function ToolbarToggle({
    items,
    active,
    onChange,
}: {
    items: Array<{ id: string; label: string; icon?: string }>;
    active: string;
    onChange: (value: string) => void;
}) {
    return (
        <div className="inline-flex items-center gap-2 rounded-md">
            {items.map((item) => (
                <Button
                    variant={"ghost"}
                    key={item.id}
                    type="button"
                    onClick={() => onChange(item.id)}
                    className={cn(
                        "h-10 rounded-none border border-[#D0D5DD] px-4 text-sm font-medium text-[#6B7280]",
                        active === item.id && "bg-[#85829940] text-[#2F3342]",
                    )}
                >
                    {item.icon ? <Image src={item.icon} alt={item.label} width={16} height={16} className="h-7 w-7" /> : null}
                    {item.label}
                </Button>
            ))}
        </div>
    );
}

export function SimpleBarChart({
    data,
    tone = "double",
    height = 180,
}: {
    data: Array<{ label: string; primary: number; secondary?: number }>;
    tone?: "double" | "stack";
    height?: number;
}) {
    const max = Math.max(...data.flatMap((item) => [item.primary, item.secondary || 0, 1]));

    return (
        <div className="space-y-4 mt-20">
            <div className="flex h-[180px] items-end gap-5">
                {data.map((item) => {
                    const primaryHeight = `${Math.max(10, (item.primary / max) * height)}px`;
                    const secondaryHeight = `${Math.max(6, ((item.secondary || 0) / max) * height)}px`;
                    return (
                        <div key={item.label} className="flex flex-1 flex-col items-center gap-2">
                            <div className="flex h-full items-end gap-1">
                                <span className="w-2 rounded-sm bg-[#A3A6B3]" style={{ height: primaryHeight }} />
                                {tone === "double" ? (
                                    <span className="w-2 rounded-sm bg-[#3D414E]" style={{ height: secondaryHeight }} />
                                ) : (
                                    <span className="w-2 rounded-sm bg-[#DADCE6]" style={{ height: secondaryHeight }} />
                                )}
                            </div>
                            <span className="text-[11px] text-[#6B7280]">{item.label}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export function SearchField({
    value,
    onChange,
    placeholder = "Search",
}: {
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
}) {
    return (
        <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#A1A1AA]" />
            <Input
                value={value}
                onChange={(event) => onChange(event.target.value)}
                placeholder={placeholder}
                className="h-10 w-[289px] rounded-none border-[#E5E7EB] bg-white pl-9"
            />
        </div>
    );
}

export function Pager({
    page,
    totalPages,
    onPrevious,
    onNext,
}: {
    page: number;
    totalPages: number;
    onPrevious?: () => void;
    onNext?: () => void;
}) {
    const canGoBack = page > 1;
    const canGoForward = page < Math.max(totalPages, 1);
    return (
        <div className="flex items-center gap-5 text-sm text-[#2F3342]">
            <button type="button" onClick={onPrevious} disabled={!canGoBack} className={cn(!canGoBack && "cursor-not-allowed text-[#C7CBD8]")}>
                <ChevronLeft className="h-4 w-4" />
            </button>
            <span>Page {page} of {Math.max(totalPages, 1)}</span>
            <button type="button" onClick={onNext} disabled={!canGoForward} className={cn(!canGoForward && "cursor-not-allowed text-[#C7CBD8]")}>
                <ChevronRight className="h-4 w-4" />
            </button>
        </div>
    );
}
