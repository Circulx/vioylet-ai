"use client";

import { CalendarDays, ChevronDown, HelpCircle, HelpCircleIcon } from "lucide-react";
import { PlatformPageTitle, SectionCard } from "@/components/platformOwner/PlatformOwnerPrimitives";
import { useBrands } from "@/hooks/useBrands";
import { useGetMe } from "@/hooks/useUser";
import { useGetTenantData, useGetTenantUsageSummary } from "@/hooks/tenantAdmins/useGetTenants";
import {
    buildMonthYearOptions,
    formatCompactMonthLabel,
    MiniMetric,
    MonthWindowPopoverButton,
    normalizeMonthWindow,
    parseUsageValue,
    ProgressRow,
} from "../Premitives";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../ui/dialog";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "../ui/collapsible";
import { Button } from "../ui/button";
import { useId, useMemo, useState } from "react";
import { buildUsageWindowRows, usagePercentage } from "@/lib/platform-owner";
import { CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Link from "next/link";
import Image from "next/image";
import { tenantDashboardFaqs } from "@/lib/faqs";

function toPercent(value?: number, max?: number) {
    if (!max || max <= 0) {
        return 0;
    }
    return Math.min(100, Math.round(((value || 0) / max) * 100));
}

const chartPalette = ["#f6c5e6", "#c7d7ff", "#fbe29c", "#c6f0d3", "#d9d0ff", "#ffd6ae"];

function formatDateLabel(value?: string) {
    if (!value) {
        return "-";
    }
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
        return "-";
    }
    return new Intl.DateTimeFormat("en-IN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
    }).format(parsed);
}

function formatLifecycleLabel(value: string) {
    if (value === "active") {
        return "Engaged";
    }
    return value.charAt(0).toUpperCase() + value.slice(1);
}

function formatMonthAxisLabel(month: string, totalMonths: number) {
    const [year, monthValue] = month.split("-").map(Number);
    if (Number.isNaN(year) || Number.isNaN(monthValue) || monthValue < 1 || monthValue > 12) {
        return month;
    }

    const parsed = new Date(year, monthValue - 1, 1);
    const shortMonth = parsed.toLocaleString("en-IN", { month: "short" });
    return totalMonths <= 6 ? `${shortMonth}'${String(parsed.getFullYear()).slice(-2)}` : shortMonth;
}

function formatCount(value: number) {
    return new Intl.NumberFormat("en-US").format(value);
}

type UsageTrendSeries = {
    dataKey: string;
    label: string;
    color: string;
};

type UsageTrendPoint = {
    month: string;
    label: string;
    [key: string]: string | number;
};

function UsageTrendChart({
    data,
    series,
    emptyMessage,
}: {
    data: UsageTrendPoint[];
    series: UsageTrendSeries[];
    emptyMessage: string;
}) {
    const chartData = data.map((item) => ({
        ...item,
        axisLabel: formatMonthAxisLabel(item.month, data.length),
    }));

    return chartData.length ? (
        <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 12, right: 8, left: 8, bottom: 8 }}>
                    <CartesianGrid vertical={false} stroke="#EEF1F6" />
                    <XAxis
                        dataKey="axisLabel"
                        axisLine={false}
                        tickLine={false}
                        interval={0}
                        minTickGap={0}
                        tickMargin={10}
                        padding={{ left: 8, right: 8 }}
                        tick={{ fill: "#475467", fontSize: 12 }}
                    />
                    <YAxis hide />
                    <Tooltip
                        cursor={{ stroke: "#D0D5DD", strokeDasharray: "4 4" }}
                        content={<UsageTrendTooltip series={series} />}
                    />
                    {series.map((item) => (
                        <Line
                            key={item.dataKey}
                            type="monotone"
                            dataKey={item.dataKey}
                            stroke={item.color}
                            strokeWidth={2.25}
                            dot={false}
                            activeDot={{ r: 4, fill: item.color, stroke: "#FFFFFF", strokeWidth: 2 }}
                            connectNulls
                        />
                    ))}
                </LineChart>
            </ResponsiveContainer>
        </div>
    ) : (
        <div className="rounded-[8px] border border-[#E4E7EC] px-4 py-10 text-center text-sm text-[#6B7280]">
            {emptyMessage}
        </div>
    );
}

function UsageTrendTooltip({
    active,
    payload,
    label,
    series,
}: {
    active?: boolean;
    payload?: Array<{ dataKey?: string; value?: number; payload?: { label?: string } }>;
    label?: string;
    series: UsageTrendSeries[];
}) {
    if (!active || !payload?.length) {
        return null;
    }

    const tooltipLabel = payload[0]?.payload?.label || label;

    return (
        <div className="rounded-[8px] border border-[#E4E7EC] bg-white px-3 py-2 text-sm shadow-[0_18px_48px_-20px_rgba(15,23,42,0.25)]">
            <p className="mb-2 font-medium text-[#2F3342]">{tooltipLabel}</p>
            <div className="space-y-1 text-[#4B5563]">
                {series.map((item) => {
                    const seriesValue = payload.find((entry) => entry.dataKey === item.dataKey)?.value || 0;
                    return (
                        <div key={item.dataKey} className="flex items-center gap-2">
                            <span className="inline-block h-4 w-4" style={{ backgroundColor: item.color }} />
                            <span>
                                {item.label}: {formatCount(seriesValue)}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

type BrandUsageSlice = {
    id: string;
    name: string;
    value: number;
    percentage: number;
    color: string;
};

type BrandUsageMetricKey = "content_generations" | "image_generations" | "ocr_pages";

function buildBrandMetricSlices(
    brands: Array<{ id: string; name: string; value: number }>,
) {
    const visibleBrands = brands.filter((brand) => brand.value > 0);
    const totalValue = visibleBrands.reduce((sum, brand) => sum + brand.value, 0);
    if (!visibleBrands.length || totalValue <= 0) {
        return [] as BrandUsageSlice[];
    }

    return visibleBrands.map((brand, index) => ({
        id: brand.id,
        name: brand.name,
        color: chartPalette[index % chartPalette.length],
        percentage: (brand.value / totalValue) * 100,
        value: brand.value,
    }));
}

function sumBrandMonthlyMetric(
    monthlyUsage: Array<{ month: string; content_generations: number; image_generations: number; ocr_pages: number }> | undefined,
    metricKey: BrandUsageMetricKey,
    startMonth: string,
    endMonth: string,
    fallbackValue: number,
) {
    if (!monthlyUsage?.length || !startMonth || !endMonth) {
        return fallbackValue;
    }

    return monthlyUsage
        .filter((row) => row.month >= startMonth && row.month <= endMonth)
        .reduce((sum, row) => sum + (row[metricKey] || 0), 0);
}

function hexToRgba(hex: string, alpha: number) {
    const normalized = hex.replace("#", "");
    const safeHex = normalized.length === 3
        ? normalized.split("").map((char) => `${char}${char}`).join("")
        : normalized.padEnd(6, "0").slice(0, 6);
    const red = parseInt(safeHex.slice(0, 2), 16);
    const green = parseInt(safeHex.slice(2, 4), 16);
    const blue = parseInt(safeHex.slice(4, 6), 16);

    return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

function BrandUsagePieChart({
    chartId,
    data,
    emptyMessage,
}: {
    chartId: string;
    data: BrandUsageSlice[];
    emptyMessage: string;
}) {
    const gradientPrefix = useId().replace(/:/g, "");
    const totalValue = data.reduce((sum, item) => sum + item.value, 0);

    if (!data.length || totalValue <= 0) {
        return (
            <div className="rounded-[8px] border border-[#E4E7EC] px-4 py-10 text-center text-sm text-[#6B7280]">
                {emptyMessage}
            </div>
        );
    }

    return (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_210px] lg:items-center">
            <div className="h-[260px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                        <defs>
                            {data.map((item) => {
                                const gradientId = `${gradientPrefix}-${chartId}-${item.id}`;
                                return (
                                    <linearGradient key={gradientId} id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" stopColor={hexToRgba(item.color, 0.96)} />
                                        <stop offset="100%" stopColor={hexToRgba(item.color, 0.72)} />
                                    </linearGradient>
                                );
                            })}
                        </defs>
                        <Tooltip content={<BrandUsagePieTooltip />} />
                        <Pie
                            data={data}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            innerRadius="42%"
                            outerRadius="76%"
                            paddingAngle={1.5}
                            cornerRadius={3}
                            stroke="none"
                            isAnimationActive={false}
                        >
                            {data.map((item) => {
                                const gradientId = `${gradientPrefix}-${chartId}-${item.id}`;
                                return <Cell key={item.id} fill={`url(#${gradientId})`} />;
                            })}
                        </Pie>
                    </PieChart>
                </ResponsiveContainer>
            </div>
            <div className="max-h-[220px] space-y-3 overflow-y-auto pr-2">
                {data.map((item) => (
                    <div key={item.id} className="flex items-center gap-3 text-sm text-[#4B5563]">
                        <span
                            className="h-4 w-4 shrink-0 rounded-[2px]"
                            style={{ background: `linear-gradient(135deg, ${hexToRgba(item.color, 0.96)} 0%, ${hexToRgba(item.color, 0.72)} 100%)` }}
                        />
                        <span className="truncate">{item.name}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function BrandUsagePieTooltip({
    active,
    payload,
}: {
    active?: boolean;
    payload?: Array<{ payload?: BrandUsageSlice }>;
}) {
    const item = payload?.[0]?.payload;
    if (!active || !item) {
        return null;
    }

    return (
        <div className="rounded-[8px] border border-[#E4E7EC] bg-white px-4 py-3 text-sm shadow-[0_18px_48px_-20px_rgba(15,23,42,0.25)]">
            <div className="flex items-center gap-2 text-[#4B5563]">
                <span
                    className="inline-block h-4 w-4 rounded-[2px]"
                    style={{ background: `linear-gradient(135deg, ${hexToRgba(item.color, 0.96)} 0%, ${hexToRgba(item.color, 0.72)} 100%)` }}
                />
                <span>{item.name} {Math.round(item.percentage)}%</span>
            </div>
        </div>
    );
}

function DashboardFaqItem({ question, answer }: { question: string; answer: string }) {
    const [open, setOpen] = useState(false);

    return (
        <Collapsible open={open} onOpenChange={setOpen} className="border-b border-[#E5E7F0] last:border-b-0">
            <CollapsibleTrigger className="flex w-full items-center justify-between gap-4 py-4 text-left">
                <span className="text-[15px] font-semibold text-[#252837]">{question}</span>
                <ChevronDown className={`h-5 w-5 shrink-0 text-primary transition-transform ${open ? "rotate-180" : ""}`} />
            </CollapsibleTrigger>
            <CollapsibleContent className="pb-4 pr-8 text-sm leading-6 text-[#5F6472]">
                {answer}
            </CollapsibleContent>
        </Collapsible>
    );
}
export default function TenantAdminDashboard() {
    const { data: currentUser } = useGetMe();
    const { data: tenant } = useGetTenantData(currentUser?.tenantId ?? "");
    const { data: usageSummary } = useGetTenantUsageSummary(currentUser?.tenantId ?? "");
    const { data: brands } = useBrands();

    const [selectedUsageMonth, setSelectedUsageMonth] = useState("");
    const [ocrStartMonth, setOcrStartMonth] = useState("");
    const [ocrEndMonth, setOcrEndMonth] = useState("");
    const [generationStartMonth, setGenerationStartMonth] = useState("");
    const [generationEndMonth, setGenerationEndMonth] = useState("");
    const [brandOcrUsageStartMonth, setBrandOcrUsageStartMonth] = useState("");
    const [brandOcrUsageEndMonth, setBrandOcrUsageEndMonth] = useState("");
    const [brandAiUsageStartMonth, setBrandAiUsageStartMonth] = useState("");
    const [brandAiUsageEndMonth, setBrandAiUsageEndMonth] = useState("");
    const [helpDialogOpen, setHelpDialogOpen] = useState(false);


    const totalCapacity = Math.round(
        [
            toPercent(usageSummary?.consumption.content_generations, usageSummary?.limits.max_content_generations),
            toPercent(usageSummary?.consumption.image_generations, usageSummary?.limits.max_image_generations),
            toPercent(usageSummary?.consumption.ocr_pages, usageSummary?.limits.max_ocr_pages),
            toPercent(usageSummary?.consumption.users, usageSummary?.limits.max_users),
            toPercent(usageSummary?.consumption.brand_spaces, usageSummary?.limits.max_brand_spaces),
        ].reduce((sum, current) => sum + current, 0) / 5,
    );
    const liveActiveBrands = useMemo(
        () => (brands || []).filter((brand) => brand.lifecycle_state !== "archived" && brand.lifecycle_state !== "deleted"),
        [brands],
    );
    const monthlyUsage = usageSummary?.monthly_usage;
    const brandUsage = usageSummary?.brand_usage;
    const brandRows = liveActiveBrands.map((brand) => ({
        name: brand.name,
        createdAt: formatDateLabel(brand.created_at),
        createdBy: currentUser?.name || "Tenant Admin",
        activeLast30Days: formatLifecycleLabel(brand.lifecycle_state),
        lastUsed: formatDateLabel(brand.updated_at),
    }));

    const usageWindow = useMemo(
        () => (tenant?.metadata_json?.usage_window as Record<string, unknown> | undefined) ?? {},
        [tenant?.metadata_json?.usage_window],
    );
    const hasUsageWindow = typeof usageWindow.start_month === "string" && typeof usageWindow.end_month === "string";
    const liveUsageRows = useMemo(
        () =>
            (brandUsage || []).map((brand) => ({
                brand: brand.name,
                contentGenerations: brand.content_generations || 0,
                visuals: brand.image_generations || 0,
                ocrPages: brand.ocr_pages || 0,
            })),
        [brandUsage],
    );

    const usageMonthOptions = useMemo(
        () => {
            if (hasUsageWindow) {
                return buildMonthYearOptions(
                    typeof usageWindow.start_month === "string" ? usageWindow.start_month : undefined,
                    typeof usageWindow.end_month === "string" ? usageWindow.end_month : undefined,
                );
            }

            if (monthlyUsage?.length) {
                return monthlyUsage.map((row) => ({
                    value: row.month,
                    label: formatCompactMonthLabel(row.month),
                }));
            }

            return buildMonthYearOptions(
                typeof usageWindow.start_month === "string" ? usageWindow.start_month : undefined,
                typeof usageWindow.end_month === "string" ? usageWindow.end_month : undefined,
            );
        },
        [hasUsageWindow, monthlyUsage, usageWindow.end_month, usageWindow.start_month],
    );

    const usageRows = useMemo(() => {
        if (!usageSummary) {
            return [];
        }

        const usageByMonth = new Map((monthlyUsage || []).map((row) => [row.month, row]));
        if (!usageMonthOptions.length) {
            return buildUsageWindowRows(usageSummary, tenant?.metadata_json);
        }

        return usageMonthOptions.map((option) => {
            const row = usageByMonth.get(option.value);
            return {
                month: option.value,
                content: `${row?.content_generations || 0}/${usageSummary.limits.max_content_generations || 0}`,
                visuals: `${row?.image_generations || 0}/${usageSummary.limits.max_image_generations || 0}`,
                ocr: `${row?.ocr_pages || 0}/${usageSummary.limits.max_ocr_pages || 0}`,
                brandSpaces: `${usageSummary.consumption.brand_spaces || 0}/${usageSummary.limits.max_brand_spaces || 0}`,
                users: `${usageSummary.consumption.users || 0}/${usageSummary.limits.max_users || 0}`,
            };
        });
    }, [monthlyUsage, tenant?.metadata_json, usageMonthOptions, usageSummary]);

     const resolvedUsageMonth = usageMonthOptions.some((option) => option.value === selectedUsageMonth)
        ? selectedUsageMonth
        : usageMonthOptions[usageMonthOptions.length - 1]?.value || "";

    const selectedUsageOption =
        usageMonthOptions.find((option) => option.value === resolvedUsageMonth) ?? usageMonthOptions[usageMonthOptions.length - 1] ?? null;

    const usageLimitRows = useMemo(
        () =>
            usageRows.map((row, index) => ({
                ...row,
                monthValue: usageMonthOptions[index]?.value || "",
                monthLabel: usageMonthOptions[index]?.label || row.month,
            })),
        [usageMonthOptions, usageRows],
    );
    const usageLimitMinMonth = usageLimitRows[0]?.monthValue || "";
    const usageLimitMaxMonth = usageLimitRows[usageLimitRows.length - 1]?.monthValue || "";
    const resolvedOcrStartMonth = usageLimitRows.some((row) => row.monthValue === ocrStartMonth)
        ? ocrStartMonth
        : usageLimitMinMonth;
    const resolvedOcrEndMonth = usageLimitRows.some((row) => row.monthValue === ocrEndMonth)
        ? ocrEndMonth
        : usageLimitMaxMonth;
    const normalizedOcrRange = useMemo(
        () => normalizeMonthWindow(resolvedOcrStartMonth, resolvedOcrEndMonth),
        [resolvedOcrEndMonth, resolvedOcrStartMonth],
    );
    const filteredOcrRows = useMemo(() => {
        if (!usageLimitRows.length) return usageLimitRows;
        if (!normalizedOcrRange.start || !normalizedOcrRange.end) {
            return usageLimitRows;
        }

        return usageLimitRows.filter((row) =>
            row.monthValue >= normalizedOcrRange.start && row.monthValue <= normalizedOcrRange.end,
        );
    }, [normalizedOcrRange.end, normalizedOcrRange.start, usageLimitRows]);
    const ocrDateLabel = useMemo(() => {
        if (!normalizedOcrRange.start || !normalizedOcrRange.end) {
            return "Select month window";
        }

        return `${formatCompactMonthLabel(normalizedOcrRange.start)} - ${formatCompactMonthLabel(normalizedOcrRange.end)}`;
    }, [normalizedOcrRange.end, normalizedOcrRange.start]);
    const ocrWindowData = useMemo(
        () =>
            filteredOcrRows.map((row) => ({
                month: row.monthValue,
                label: row.monthLabel,
                ocrPages: parseUsageValue(row.ocr).used,
            })),
        [filteredOcrRows],
    );
    const resolvedGenerationStartMonth = usageLimitRows.some((row) => row.monthValue === generationStartMonth)
        ? generationStartMonth
        : usageLimitMinMonth;
    const resolvedGenerationEndMonth = usageLimitRows.some((row) => row.monthValue === generationEndMonth)
        ? generationEndMonth
        : usageLimitMaxMonth;
    const normalizedGenerationRange = useMemo(
        () => normalizeMonthWindow(resolvedGenerationStartMonth, resolvedGenerationEndMonth),
        [resolvedGenerationEndMonth, resolvedGenerationStartMonth],
    );
    const filteredGenerationRows = useMemo(() => {
        if (!usageLimitRows.length) return usageLimitRows;
        if (!normalizedGenerationRange.start || !normalizedGenerationRange.end) {
            return usageLimitRows;
        }

        return usageLimitRows.filter((row) =>
            row.monthValue >= normalizedGenerationRange.start && row.monthValue <= normalizedGenerationRange.end,
        );
    }, [normalizedGenerationRange.end, normalizedGenerationRange.start, usageLimitRows]);
    const generationDateLabel = useMemo(() => {
        if (!normalizedGenerationRange.start || !normalizedGenerationRange.end) {
            return "Select month window";
        }

        return `${formatCompactMonthLabel(normalizedGenerationRange.start)} - ${formatCompactMonthLabel(normalizedGenerationRange.end)}`;
    }, [normalizedGenerationRange.end, normalizedGenerationRange.start]);
    const generationWindowData = useMemo(
        () =>
            filteredGenerationRows.map((row) => {
                const contentMetric = parseUsageValue(row.content);
                const visualsMetric = parseUsageValue(row.visuals);
                return {
                    month: row.monthValue,
                    label: row.monthLabel,
                    visuals: visualsMetric.used,
                    content: contentMetric.used,
                };
            }),
        [filteredGenerationRows],
    );
    const resolvedBrandOcrUsageStartMonth = usageLimitRows.some((row) => row.monthValue === brandOcrUsageStartMonth)
        ? brandOcrUsageStartMonth
        : usageLimitMinMonth;
    const resolvedBrandOcrUsageEndMonth = usageLimitRows.some((row) => row.monthValue === brandOcrUsageEndMonth)
        ? brandOcrUsageEndMonth
        : usageLimitMaxMonth;
    const normalizedBrandOcrUsageRange = useMemo(
        () => normalizeMonthWindow(resolvedBrandOcrUsageStartMonth, resolvedBrandOcrUsageEndMonth),
        [resolvedBrandOcrUsageEndMonth, resolvedBrandOcrUsageStartMonth],
    );
    const brandOcrUsageDateLabel = useMemo(() => {
        if (!normalizedBrandOcrUsageRange.start || !normalizedBrandOcrUsageRange.end) {
            return "Select month window";
        }

        return `${formatCompactMonthLabel(normalizedBrandOcrUsageRange.start)} - ${formatCompactMonthLabel(normalizedBrandOcrUsageRange.end)}`;
    }, [normalizedBrandOcrUsageRange.end, normalizedBrandOcrUsageRange.start]);
    const resolvedBrandAiUsageStartMonth = usageLimitRows.some((row) => row.monthValue === brandAiUsageStartMonth)
        ? brandAiUsageStartMonth
        : usageLimitMinMonth;
    const resolvedBrandAiUsageEndMonth = usageLimitRows.some((row) => row.monthValue === brandAiUsageEndMonth)
        ? brandAiUsageEndMonth
        : usageLimitMaxMonth;
    const normalizedBrandAiUsageRange = useMemo(
        () => normalizeMonthWindow(resolvedBrandAiUsageStartMonth, resolvedBrandAiUsageEndMonth),
        [resolvedBrandAiUsageEndMonth, resolvedBrandAiUsageStartMonth],
    );
    const brandAiUsageDateLabel = useMemo(() => {
        if (!normalizedBrandAiUsageRange.start || !normalizedBrandAiUsageRange.end) {
            return "Select month window";
        }

        return `${formatCompactMonthLabel(normalizedBrandAiUsageRange.start)} - ${formatCompactMonthLabel(normalizedBrandAiUsageRange.end)}`;
    }, [normalizedBrandAiUsageRange.end, normalizedBrandAiUsageRange.start]);
    const brandOcrSlices = useMemo(
        () =>
            buildBrandMetricSlices(
                (brandUsage || []).map((brand) => ({
                    id: brand.id,
                    name: brand.name,
                    value: sumBrandMonthlyMetric(
                        brand.monthly_usage,
                        "ocr_pages",
                        normalizedBrandOcrUsageRange.start,
                        normalizedBrandOcrUsageRange.end,
                        brand.ocr_pages || 0,
                    ),
                })),
            ),
        [brandUsage, normalizedBrandOcrUsageRange.end, normalizedBrandOcrUsageRange.start],
    );
    const brandAiSlices = useMemo(
        () =>
            buildBrandMetricSlices(
                (brandUsage || []).map((brand) => ({
                    id: brand.id,
                    name: brand.name,
                    value: sumBrandMonthlyMetric(
                        brand.monthly_usage,
                        "image_generations",
                        normalizedBrandAiUsageRange.start,
                        normalizedBrandAiUsageRange.end,
                        brand.image_generations || 0,
                    ),
                })),
            ),
        [brandUsage, normalizedBrandAiUsageRange.end, normalizedBrandAiUsageRange.start],
    );

    const resetOcrWindow = () => {
        setOcrStartMonth(usageLimitMinMonth);
        setOcrEndMonth(usageLimitMaxMonth);
    };
    const resetGenerationWindow = () => {
        setGenerationStartMonth(usageLimitMinMonth);
        setGenerationEndMonth(usageLimitMaxMonth);
    };
    const resetBrandOcrUsageWindow = () => {
        setBrandOcrUsageStartMonth(usageLimitMinMonth);
        setBrandOcrUsageEndMonth(usageLimitMaxMonth);
    };
    const resetBrandAiUsageWindow = () => {
        setBrandAiUsageStartMonth(usageLimitMinMonth);
        setBrandAiUsageEndMonth(usageLimitMaxMonth);
    };

    const selectedUsageMetrics = (() => {
        const fallbackMetrics = {
            totalCapacity,
            contentPercent: usagePercentage(usageSummary?.consumption.content_generations || 0, usageSummary?.limits.max_content_generations || 0),
            visualsPercent: usagePercentage(usageSummary?.consumption.image_generations || 0, usageSummary?.limits.max_image_generations || 0),
            ocrPercent: usagePercentage(usageSummary?.consumption.ocr_pages || 0, usageSummary?.limits.max_ocr_pages || 0),
            brandSpacesUsed: usageSummary?.consumption.brand_spaces || 0,
            brandSpacesLimit: usageSummary?.limits.max_brand_spaces || 0,
            usersUsed: usageSummary?.consumption.users || 0,
            usersLimit: usageSummary?.limits.max_users || 0,
        };

        const selectedIndex = usageMonthOptions.findIndex((option) => option.value === resolvedUsageMonth);
        const selectedRow = selectedIndex >= 0 ? usageRows[selectedIndex] : null;
        if (!selectedRow) {
            return fallbackMetrics;
        }

        const contentMetric = parseUsageValue(selectedRow.content);
        const visualsMetric = parseUsageValue(selectedRow.visuals);
        const ocrMetric = parseUsageValue(selectedRow.ocr);
        const brandSpacesMetric = parseUsageValue(selectedRow.brandSpaces);
        const usersMetric = parseUsageValue(selectedRow.users);

        return {
            totalCapacity: usagePercentage(
                contentMetric.used + visualsMetric.used + ocrMetric.used,
                contentMetric.limit + visualsMetric.limit + ocrMetric.limit,
            ),
            contentPercent: usagePercentage(contentMetric.used, contentMetric.limit),
            visualsPercent: usagePercentage(visualsMetric.used, visualsMetric.limit),
            ocrPercent: usagePercentage(ocrMetric.used, ocrMetric.limit),
            brandSpacesUsed: brandSpacesMetric.used,
            brandSpacesLimit: brandSpacesMetric.limit,
            usersUsed: usersMetric.used,
            usersLimit: usersMetric.limit,
        };
    })();

    return (
        <div className="container">
            <div className="space-y-6">
                <PlatformPageTitle
                    title={`${tenant?.name}'s Dashboard`}
                    action={
                        <Button
                            type="button"
                            onClick={() => setHelpDialogOpen(true)}
                            className="h-12 rounded-none bg-primary/10 text-black px-5 text-[15px] font-medium hover:bg-primary/17"
                        >
                            <Image src={"actions_icons/info_circle.svg"} alt="info" width={16} height={16} />
                            Help
                        </Button>
                    }
                />
                <Dialog open={helpDialogOpen} onOpenChange={setHelpDialogOpen}>
                    <DialogContent className="max-h-[84vh] w-full max-w-[620px] overflow-y-auto rounded-none border-0 bg-white p-0 shadow-[0_24px_90px_-28px_rgba(15,23,42,0.45)]">
                        <DialogHeader className="border-b border-[#E5E7F0] px-6 py-5 text-left">
                            <DialogTitle className="text-[24px] font-bold leading-tight text-primary">Frequently Asked Questions</DialogTitle>
                            <DialogDescription className="text-sm text-[#5F6472]">
                                Quick answers for tenant dashboard usage, capacity, and reporting.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="px-6 py-2">
                            {tenantDashboardFaqs.map((faq) => (
                                <DashboardFaqItem key={faq.id} question={faq.question} answer={faq.answer} />
                            ))}
                        </div>
                    </DialogContent>
                </Dialog>                <SectionCard title="Monthly Usage"
                    toolbar={
                        <Popover>
                            <PopoverTrigger asChild>
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="h-10 rounded-xs border-[#D5D8E8] bg-white px-3 text-sm font-medium text-[#4B5563] shadow-none hover:bg-[#FAFAFD]"
                                >
                                    <CalendarDays className="mr-2 h-4 w-4 text-[#4B5563]" />
                                    {selectedUsageOption?.label || "Select month"}
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent align="end" className="w-45 rounded-[10px] border border-[#D5D8E8] bg-white p-2 shadow-[0_18px_48px_-20px_rgba(15,23,42,0.35)]">
                                <div className="space-y-1">
                                    {usageMonthOptions.map((option) => {
                                        const isActive = option.value === resolvedUsageMonth;
                                        return (
                                            <button
                                                key={option.value}
                                                type="button"
                                                onClick={() => setSelectedUsageMonth(option.value)}
                                                className={`w-full rounded-[8px] px-3 py-2 text-left text-sm font-medium transition ${isActive
                                                    ? "bg-[#F5F6FB] text-[#2F3342]"
                                                    : "text-[#6B7280] hover:bg-[#FAFAFD]"
                                                    }`}
                                            >
                                                {option.label}
                                            </button>
                                        );
                                    })}
                                </div>
                            </PopoverContent>
                        </Popover>
                    }
                >
                    <div className="space-y-4">
                        <ProgressRow label="Total Capacity" info value={selectedUsageMetrics.totalCapacity} icon="/tenants/capacity.svg" />
                        <div className="grid gap-4 md:grid-cols-3">
                            <MiniMetric label="Content" progress={true} value={selectedUsageMetrics.contentPercent} icon="/tenants/content.svg" />
                            <MiniMetric label="Visuals" progress={true} value={selectedUsageMetrics.visualsPercent} icon="/tenants/visuals.svg" />
                            <MiniMetric label="OCR Pages" progress={true} value={selectedUsageMetrics.ocrPercent} icon="/tenants/ocr_pages.svg" />
                        </div>
                    </div>

                </SectionCard>
                <div className="grid gap-4 md:grid-cols-2">
                    <MiniMetric label="Brand Space" value={selectedUsageMetrics.brandSpacesUsed} helper={`${selectedUsageMetrics.brandSpacesLimit}`} compact icon="/tenants/brand_spaces.svg" />
                    <MiniMetric label="Users" value={selectedUsageMetrics.usersUsed} helper={`${selectedUsageMetrics.usersLimit}`} compact icon="/tenants/users.svg" />
                </div>

                <div className="grid gap-4 xl:grid-cols-2">
                    <SectionCard
                        title="Total OCR Pages"
                        className="min-h-96"
                        toolbar={
                            <MonthWindowPopoverButton
                                label={ocrDateLabel}
                                startMonth={resolvedOcrStartMonth}
                                endMonth={resolvedOcrEndMonth}
                                minMonth={usageLimitMinMonth}
                                maxMonth={usageLimitMaxMonth}
                                onStartChange={setOcrStartMonth}
                                onEndChange={setOcrEndMonth}
                                onReset={resetOcrWindow}
                            />
                        }
                    >
                        <div className={!ocrWindowData.length ? "pt-[60px]" : undefined}>
                            <UsageTrendChart
                                data={ocrWindowData}
                                series={[{ dataKey: "ocrPages", label: "OCR Pages", color: "#7E7E7E" }]}
                                emptyMessage="No OCR usage is available for the selected window."
                            />
                        </div>
                    </SectionCard>

                    <SectionCard
                        title="Total Generations"
                        className="min-h-96"
                        toolbar={
                            <MonthWindowPopoverButton
                                label={generationDateLabel}
                                startMonth={resolvedGenerationStartMonth}
                                endMonth={resolvedGenerationEndMonth}
                                minMonth={usageLimitMinMonth}
                                maxMonth={usageLimitMaxMonth}
                                onStartChange={setGenerationStartMonth}
                                onEndChange={setGenerationEndMonth}
                                onReset={resetGenerationWindow}
                            />
                        }
                    >
                        <div className="space-y-5">
                            <div className="space-y-2 text-xs text-slate-500">
                                <div className="flex items-center gap-2">
                                    <span className="inline-block h-4 w-4 bg-[#A9A9A9]" />
                                    <span>Visuals</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="inline-block h-4 w-4 bg-[#595959]" />
                                    <span>Content</span>
                                </div>
                            </div>
                            <UsageTrendChart
                                data={generationWindowData}
                                series={[
                                    { dataKey: "visuals", label: "Visuals", color: "#A9A9A9" },
                                    { dataKey: "content", label: "Content", color: "#595959" },
                                ]}
                                emptyMessage="No generation usage is available for the selected window."
                            />
                        </div>
                    </SectionCard>
                </div>

                <SectionCard title="Brand Wise Activity" className="border-none p-0" >
                    <div className="overflow-x-auto">
                        <table className="table">
                            <thead>
                                <tr className="bg-slate-100/50 text-black">
                                    <th className="w-1/6 border-2 border-white px-5 py-3 font-medium text-black">Name</th>
                                    <th className="w-1/6 border-2 border-white px-5 py-3 font-medium text-black">Date Created</th>
                                    <th className="w-1/6 border-2 border-white px-5 py-3 font-medium text-black">Created By</th>
                                    <th className="w-1/6 border-2 border-white px-5 py-3 font-medium text-black">Active (Last 30 Days)</th>
                                    <th className="w-1/6 border-2 border-white px-5 py-3 font-medium text-black">Last Used</th>
                                </tr>
                            </thead>
                            <tbody>
                                {brandRows.map((brand) => (
                                    <tr key={brand.name} className="bg-slate-100/50 text-[#666666]">
                                        <td className="w-1/6 border-2 border-white px-5 py-3">{brand.name}</td>
                                        <td className="w-1/6 border-2 border-white px-5 py-3">{brand.createdAt}</td>
                                        <td className="w-1/6 border-2 border-white px-5 py-3">{brand.createdBy}</td>
                                        <td className="w-1/6 border-2 border-white px-5 py-3">{brand.activeLast30Days}</td>
                                        <td className="w-1/6 border-2 border-white px-5 py-3">{brand.lastUsed}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </SectionCard>

                <div className="grid gap-4 xl:grid-cols-2">
                    <SectionCard
                        title="Brand OCR Usage"
                        toolbar={
                            <MonthWindowPopoverButton
                                label={brandOcrUsageDateLabel}
                                startMonth={resolvedBrandOcrUsageStartMonth}
                                endMonth={resolvedBrandOcrUsageEndMonth}
                                minMonth={usageLimitMinMonth}
                                maxMonth={usageLimitMaxMonth}
                                onStartChange={setBrandOcrUsageStartMonth}
                                onEndChange={setBrandOcrUsageEndMonth}
                                onReset={resetBrandOcrUsageWindow}
                            />
                        }
                    >
                        <BrandUsagePieChart
                            chartId="brand-ocr"
                            data={brandOcrSlices}
                            emptyMessage="No brand OCR usage is available for the selected window."
                        />
                    </SectionCard>

                    <SectionCard
                        title="Brand AI Usage"
                        toolbar={
                            <MonthWindowPopoverButton
                                label={brandAiUsageDateLabel}
                                startMonth={resolvedBrandAiUsageStartMonth}
                                endMonth={resolvedBrandAiUsageEndMonth}
                                minMonth={usageLimitMinMonth}
                                maxMonth={usageLimitMaxMonth}
                                onStartChange={setBrandAiUsageStartMonth}
                                onEndChange={setBrandAiUsageEndMonth}
                                onReset={resetBrandAiUsageWindow}
                            />
                        }
                    >
                        <BrandUsagePieChart
                            chartId="brand-ai"
                            data={brandAiSlices}
                            emptyMessage="No brand AI usage is available for the selected window."
                        />
                    </SectionCard>
                </div>

                <SectionCard title="Usage Overview" className="border-none p-0">
                    <div className="overflow-x-auto">
                        <table className="table">
                            <thead>
                                <tr className="bg-slate-100/50 text-black">
                                    <th className="w-1/6 border-2 border-white px-5 py-3 font-medium text-black">Brand</th>
                                    <th className="w-1/6 border-2 border-white px-5 py-3 font-medium text-black">Content Generations</th>
                                    <th className="w-1/6 border-2 border-white px-5 py-3 font-medium text-black">Visuals</th>
                                    <th className="w-1/6 border-2 border-white px-5 py-3 font-medium text-black">OCR Pages</th>
                                </tr>
                            </thead>
                            <tbody>
                                {liveUsageRows.map((row) => (
                                    <tr key={row.brand} className="bg-slate-100/50 text-[#666666]">
                                        <td className="w-1/6 border-2 border-white px-5 py-3">{row.brand}</td>
                                        <td className="w-1/6 border-2 border-white px-5 py-3">{row.contentGenerations}</td>
                                        <td className="w-1/6 border-2 border-white px-5 py-3">{row.visuals}</td>
                                        <td className="w-1/6 border-2 border-white px-5 py-3">{row.ocrPages}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </SectionCard>
            </div>
        </div>
    );
}
