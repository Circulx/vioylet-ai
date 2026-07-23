"use client";

import { ReactNode, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";

function formatHistoryTimestamp(value: string) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return "";
    }
    const formattedDate = new Intl.DateTimeFormat("en-GB", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
    }).format(date);
    const formattedTime = new Intl.DateTimeFormat("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
    }).format(date);
    return `${formattedDate} | ${formattedTime}`;
}

export function BrandSpaceHistoryDrawer({
    brandId,
    children,
}: {
    brandId?: string | null;
    children: ReactNode;
}) {
    const [open, setOpen] = useState(false);
    const { data: historyEntries = [], isError, isLoading, refetch } = useQuery({
        queryKey: ["brand-space-history", brandId],
        enabled: open && Boolean(brandId),
        queryFn: () => request(API.BRANDS.HISTORY, { pathParams: brandId || "" }),
        refetchOnWindowFocus: "always",
    });

    return (
        <Sheet
            open={open}
            onOpenChange={(nextOpen) => {
                setOpen(nextOpen);
                if (nextOpen && brandId) {
                    void refetch();
                }
            }}
        >
            <SheetTrigger asChild>{children}</SheetTrigger>
            <SheetContent className="overflow-hidden font-dmSans">
                <SheetHeader>
                    <SheetTitle className="text-2xl font-bold text-primary">History</SheetTitle>
                    <SheetDescription className="text-sm text-[#525252]">
                        View Brand Space activity history.
                    </SheetDescription>
                </SheetHeader>
                <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 pr-2 pb-4">
                    {isLoading ? (
                        <p className="py-6 text-sm text-[#525252]">Loading history...</p>
                    ) : isError ? (
                        <p className="py-6 text-sm text-[#525252]">Unable to load history right now.</p>
                    ) : historyEntries.length ? (
                        historyEntries.map((entry) => (
                            <div key={entry.id} className="rounded-[6px] border border-[#DCDCDC] bg-white px-4 py-3 shadow-sm">
                                <div className="flex items-start justify-between gap-4">
                                    <p className="min-w-0 text-sm font-semibold leading-5 text-[#252525]">{entry.message}</p>
                                    <span className="shrink-0 whitespace-nowrap text-xs text-[#525252]">
                                        {formatHistoryTimestamp(entry.created_at)}
                                    </span>
                                </div>
                            </div>
                        ))
                    ) : (
                        <p className="py-6 text-sm text-[#525252]">No history yet.</p>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    );
}
