"use client";

import { useMemo, useState, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, Box, CalendarDays, ChevronDown, Clock3, Grid2X2, Users } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { AnalyticsResponse, TenantSummaryResponse } from "@/lib/api/contracts";
import {
  buildTenantBreakdownRows,
  formatTenantDisplayName,
  getActivityLabel,
  usagePercentage,
} from "@/lib/platform-owner";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const PASTEL = ["#FAD4EC", "#DDEEFF", "#FFEDAE", "#BDF4D4", "#D8CCFF", "#FFD7B0"];
const STATIC_BRAND_ALIGNMENT = [64, 66, 65, 68, 67, 71, 74, 72, 78, 80, 77, 84];
const STATIC_RESPONSE_TIME_SECONDS = 150;
const STATIC_BRAND_ALIGNMENT_SCORE = 85;
const STATIC_METRICS = {
  activeTenants: 15,
  totalTenants: 20,
  brandSpaces: 35,
  users: 45,
};
const DEFAULT_DATE_WINDOW = { start: "2026-01", end: "2026-12" };
const STATIC_PROVIDER_TOKEN_TRENDS = {
  openai: {
    input: [420, 330, 520, 360, 450, 160, 290, 380, 470, 510, 470, 590],
    output: [310, 210, 250, 230, 220, 90, 360, 200, 390, 390, 380, 500],
  },
  anthropic: {
    input: [260, 280, 340, 310, 350, 120, 240, 280, 320, 360, 340, 410],
    output: [190, 170, 220, 190, 210, 70, 250, 160, 260, 280, 270, 330],
  },
};
const STATIC_TENANT_PROVIDER_TOKENS = {
  openai: {
    input: [420, 310, 520, 310, 330, 150, 260, 300, 460, 470, 460, 600],
    output: [320, 220, 230, 220, 210, 90, 350, 180, 370, 370, 360, 520],
  },
  anthropic: {
    input: [250, 220, 340, 210, 260, 100, 190, 230, 300, 320, 310, 390],
    output: [170, 150, 210, 140, 160, 60, 220, 130, 230, 250, 240, 300],
  },
};

type Provider = "openai" | "anthropic";
type DateWindow = { start: string; end: string };
type DateWindowKey =
  | "summary"
  | "brandAlignment"
  | "health"
  | "ocrTrend"
  | "imageTrend"
  | "llmTokens"
  | "ocrPie"
  | "imagePie"
  | "capacity"
  | "tenantTokens";

type MetricRecord = Record<string, unknown>;
type TokenUsage = {
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  monthly_token_usage?: Array<{ month: string; input_tokens: number; output_tokens: number; total_tokens?: number }>;
};

type ChartPoint = {
  label: string;
  month?: string;
  input?: number;
  output?: number;
  value?: number;
  total?: number;
  used?: number;
};

function asNumber(value: unknown, fallback = 0) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : fallback;
}

function compactNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(Math.round(value));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function tokenUsageFromAnalytics(analytics?: AnalyticsResponse): TokenUsage {
  const metrics = (analytics?.metrics || {}) as MetricRecord;
  return (metrics.token_usage || {}) as TokenUsage;
}

function formatMonthLabel(value: string) {
  const [, month] = value.split("-");
  const monthIndex = Number(month) - 1;
  return MONTHS[monthIndex] || value;
}

function formatMonthShort(value: string) {
  const [year, month] = value.split("-");
  const monthIndex = Number(month) - 1;
  if (!year || Number.isNaN(monthIndex) || monthIndex < 0 || monthIndex > 11) {
    return value;
  }
  return `${MONTHS[monthIndex]}'${year.slice(-2)}`;
}

function formatDateWindow(value: DateWindow) {
  return `${formatMonthShort(value.start)} - ${formatMonthShort(value.end)}`;
}

function normalizeDateWindow(value: DateWindow): DateWindow {
  if (value.start <= value.end) {
    return value;
  }
  return { start: value.end, end: value.start };
}

function monthKeyFromIndex(index: number, year = 2026) {
  return `${year}-${String(index + 1).padStart(2, "0")}`;
}

function monthKeyFromDate(value?: string | null) {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "";
  }
  return `${parsed.getFullYear()}-${String(parsed.getMonth() + 1).padStart(2, "0")}`;
}

function isMonthInWindow(month: string | undefined, window: DateWindow) {
  if (!month) {
    return false;
  }
  const normalized = normalizeDateWindow(window);
  return month >= normalized.start && month <= normalized.end;
}

function filterChartByWindow<T extends ChartPoint>(data: T[], window: DateWindow) {
  return data.filter((item) => isMonthInWindow(item.month, window));
}

function filterMonthlyUsageByWindow<T extends { month: string }>(data: T[], window: DateWindow) {
  return data.filter((item) => isMonthInWindow(item.month, window));
}

function filterTenantsByWindow(tenants: TenantSummaryResponse[], window: DateWindow) {
  const normalized = normalizeDateWindow(window);
  return tenants.filter((tenant) => {
    const createdMonth = monthKeyFromDate(tenant.created_at);
    if (!createdMonth) {
      return true;
    }
    return createdMonth <= normalized.end;
  });
}

function createSyntheticTrend(total: number, minimum = 20) {
  const base = Math.max(total || minimum, minimum);
  return MONTHS.map((label, index) => ({
    label,
    month: monthKeyFromIndex(index),
    value: Math.round(base * (0.52 + index * 0.035 + (index % 3) * 0.025)),
  }));
}

function createStaticTokenTrend(provider: Provider) {
  const providerData = STATIC_PROVIDER_TOKEN_TRENDS[provider];
  return MONTHS.map((label, index) => ({
    label,
    month: monthKeyFromIndex(index),
    input: providerData.input[index],
    output: providerData.output[index],
  }));
}

function getTenantCapacity(tenant: TenantSummaryResponse) {
  const usage = tenant.usage_consumption || {};
  const limits = tenant.usage_limits;
  const used =
    asNumber(usage.content_generations) +
    asNumber(usage.image_generations) +
    asNumber(usage.ocr_pages);
  const total =
    asNumber(limits?.max_content_generations) +
    asNumber(limits?.max_image_generations) +
    asNumber(limits?.max_ocr_pages);
  return usagePercentage(used, total);
}

function buildTenantPieData(
  tenants: TenantSummaryResponse[],
  metric: "ocr_pages" | "image_generations",
  allowStaticFallback = true,
) {
  const live = tenants
    .map((tenant) => ({
      name: formatTenantDisplayName(tenant.name),
      value: asNumber(tenant.usage_consumption?.[metric]),
    }))
    .filter((item) => item.value > 0);

  if (!live.length && !allowStaticFallback) {
    return [];
  }

  const source = live.length
    ? live
    : [
        { name: "IndoSakura", value: 20 },
        { name: "DxMinds", value: 40 },
        { name: "Red & Blue Digital", value: 12 },
        { name: "A1", value: 15 },
        { name: "DelMar", value: 4 },
        { name: "Califo", value: 9 },
      ];

  return source.slice(0, 6).map((item, index) => ({
    ...item,
    fill: PASTEL[index % PASTEL.length],
  }));
}

function getNestedValue(source: unknown, path: string[]) {
  let current = source;
  for (const key of path) {
    if (!isRecord(current)) {
      return undefined;
    }
    current = current[key];
  }
  return current;
}

function getTokenMetric(source: Record<string, unknown>, key: "input_tokens" | "output_tokens") {
  return asNumber(source[key]);
}

function hasTokenMetrics(source: Record<string, unknown>) {
  return "input_tokens" in source || "output_tokens" in source;
}

function resolveProviderMetrics(entry: Record<string, unknown>, provider: Provider) {
  const directCandidate = entry[provider];
  if (isRecord(directCandidate)) {
    return directCandidate;
  }

  const providersCandidate = entry.providers;
  if (isRecord(providersCandidate) && isRecord(providersCandidate[provider])) {
    return providersCandidate[provider];
  }

  const providerUsageCandidate = entry.provider_usage;
  if (isRecord(providerUsageCandidate) && isRecord(providerUsageCandidate[provider])) {
    return providerUsageCandidate[provider];
  }

  return null;
}

function getProviderLabel(entry: Record<string, unknown>) {
  if (typeof entry.provider === "string") {
    return entry.provider.toLowerCase();
  }
  if (typeof entry.model_provider === "string") {
    return entry.model_provider.toLowerCase();
  }
  return "";
}

function normalizeTokenUsageEntry(entry: unknown, provider: Provider, requireProviderMatch = false) {
  if (!isRecord(entry) || typeof entry.month !== "string") {
    return [] as Array<{ month: string; input_tokens: number; output_tokens: number }>;
  }

  const providerLabel = getProviderLabel(entry);
  if (requireProviderMatch && providerLabel && providerLabel !== provider) {
    return [];
  }

  if (hasTokenMetrics(entry) && (!requireProviderMatch || !providerLabel || providerLabel === provider)) {
    return [{
      month: entry.month,
      input_tokens: getTokenMetric(entry, "input_tokens"),
      output_tokens: getTokenMetric(entry, "output_tokens"),
    }];
  }

  const providerUsage = resolveProviderMetrics(entry, provider);
  if (!providerUsage) {
    return [];
  }

  return [{
    month: entry.month,
    input_tokens: getTokenMetric(providerUsage, "input_tokens"),
    output_tokens: getTokenMetric(providerUsage, "output_tokens"),
  }];
}

function collapseMonthlyUsage(items: Array<{ month: string; input_tokens: number; output_tokens: number }>) {
  const monthMap = new Map<string, { month: string; input_tokens: number; output_tokens: number }>();
  items.forEach((item) => {
    if (!item.month) {
      return;
    }
    const current = monthMap.get(item.month) || { month: item.month, input_tokens: 0, output_tokens: 0 };
    monthMap.set(item.month, {
      month: item.month,
      input_tokens: current.input_tokens + item.input_tokens,
      output_tokens: current.output_tokens + item.output_tokens,
    });
  });
  return Array.from(monthMap.values()).sort((left, right) => left.month.localeCompare(right.month));
}

function normalizeProviderTokenUsage(value: unknown, provider: Provider, requireProviderMatch = false) {
  if (Array.isArray(value)) {
    return collapseMonthlyUsage(value.flatMap((entry) => normalizeTokenUsageEntry(entry, provider, requireProviderMatch)));
  }

  if (!isRecord(value)) {
    return [] as Array<{ month: string; input_tokens: number; output_tokens: number }>;
  }

  if (typeof value.month === "string") {
    return collapseMonthlyUsage(normalizeTokenUsageEntry(value, provider, requireProviderMatch));
  }

  return collapseMonthlyUsage(
    Object.entries(value).flatMap(([month, entry]) => {
      if (!isRecord(entry)) {
        return [];
      }
      return [{
        month,
        input_tokens: getTokenMetric(entry, "input_tokens"),
        output_tokens: getTokenMetric(entry, "output_tokens"),
      }];
    }),
  );
}

function resolveTenantProviderMonthlyUsage(tenant: TenantSummaryResponse, provider: Provider) {
  const metadata = isRecord(tenant.metadata_json) ? tenant.metadata_json : {};
  const providerCandidates = [
    getNestedValue(metadata, ["llm_token_usage", "providers", provider, "monthly_token_usage"]),
    getNestedValue(metadata, ["llm_token_usage", provider, "monthly_token_usage"]),
    getNestedValue(metadata, ["provider_token_usage", provider, "monthly_token_usage"]),
    getNestedValue(metadata, ["token_usage", "providers", provider, "monthly_token_usage"]),
    getNestedValue(metadata, ["token_usage", provider, "monthly_token_usage"]),
    getNestedValue(tenant, ["llm_token_usage", "providers", provider, "monthly_token_usage"]),
    getNestedValue(tenant, ["token_usage", "providers", provider, "monthly_token_usage"]),
  ];

  for (const candidate of providerCandidates) {
    const normalized = normalizeProviderTokenUsage(candidate, provider);
    if (normalized.length) {
      return normalized;
    }
  }

  return normalizeProviderTokenUsage(tenant.monthly_token_usage, provider, true);
}

function toTokenBars(items: Array<{ month: string; input_tokens: number; output_tokens: number }>) {
  return items.map((item) => ({
    label: formatMonthLabel(item.month),
    month: item.month,
    input: asNumber(item.input_tokens),
    output: asNumber(item.output_tokens),
  }));
}

function buildMonthlyTokenBars(analytics: AnalyticsResponse | undefined, tenants: TenantSummaryResponse[], provider: Provider) {
  const providerMonthly = collapseMonthlyUsage(
    tenants.flatMap((tenant) => resolveTenantProviderMonthlyUsage(tenant, provider)),
  );
  if (providerMonthly.length) {
    return toTokenBars(providerMonthly).slice(-12);
  }

  const monthly = tokenUsageFromAnalytics(analytics).monthly_token_usage || [];
  if (monthly.length && provider === "openai") {
    return toTokenBars(monthly).slice(-12);
  }

  return createStaticTokenTrend(provider);
}

function buildTenantTokenBars(tenants: TenantSummaryResponse[], provider: Provider, window: DateWindow) {
  const providerScoped = tenants
    .map((tenant) => {
      const monthly = filterMonthlyUsageByWindow(resolveTenantProviderMonthlyUsage(tenant, provider), window);
      const input = monthly.reduce((sum, item) => sum + item.input_tokens, 0);
      const output = monthly.reduce((sum, item) => sum + item.output_tokens, 0);
      return {
        label: formatTenantDisplayName(tenant.name),
        input,
        output,
      };
    })
    .filter((item) => item.input || item.output);

  if (providerScoped.length) {
    return providerScoped.slice(0, 12);
  }

  const live = tenants
    .map((tenant) => ({
      label: formatTenantDisplayName(tenant.name),
      input: asNumber(tenant.token_usage?.input_tokens),
      output: asNumber(tenant.token_usage?.output_tokens),
    }))
    .filter((item) => item.input || item.output);

  if (live.length) {
    return live.slice(0, 12);
  }

  const providerData = STATIC_TENANT_PROVIDER_TOKENS[provider];
  return [
    "IndoSakura",
    "DxMinds",
    "Red & Blue Digital",
    "A1",
    "A2",
    "A3",
    "A4",
    "Aug",
    "A5",
    "A6",
    "A7",
    "A8",
  ].map((label, index) => ({
    label,
    input: providerData.input[index],
    output: providerData.output[index],
  }));
}

function buildCapacityBars(tenants: TenantSummaryResponse[]) {
  const live = tenants.map((tenant) => ({
    label: formatTenantDisplayName(tenant.name),
    total: 100,
    used: getTenantCapacity(tenant),
  }));

  if (live.length) {
    return live.slice(0, 12);
  }

  return ["IndoSakura", "Dxminds", "Red & Blue Digital", "A1", "A2", "A3", "A4", "Aug", "A5", "A6", "A7", "A8"].map(
    (label, index) => ({
      label,
      total: 100,
      used: [72, 36, 72, 28, 35, 62, 72, 36, 58, 36, 58, 36][index],
    }),
  );
}

function buildTopRiskRows(tenants: TenantSummaryResponse[]) {
  const live = buildTenantBreakdownRows(tenants)
    .map((tenant, index) => ({
      id: tenant.id,
      name: tenant.name,
      alignment: Math.max(30, STATIC_BRAND_ALIGNMENT_SCORE - index * 8),
      capacity: tenant.capacityUsed,
      brandSpaces: tenant.brandSpaces,
      activity: getActivityLabel(tenant.activeDate),
    }))
    .sort((left, right) => right.capacity - left.capacity)
    .slice(0, 4);

  if (live.length) {
    return live;
  }

  return Array.from({ length: 4 }, (_, index) => ({
    id: `static-risk-${index}`,
    name: "Sushi",
    alignment: 30,
    capacity: 95,
    brandSpaces: 10,
    activity: index === 3 ? "Engaged" : "Dormant",
  }));
}

function totalTokenUsageFromBars(data: ChartPoint[]): TokenUsage {
  const input = data.reduce((sum, item) => sum + asNumber(item.input), 0);
  const output = data.reduce((sum, item) => sum + asNumber(item.output), 0);
  return {
    input_tokens: input,
    output_tokens: output,
    total_tokens: input + output,
  };
}

export default function PlatformOwnerDashboard({
  analytics,
  tenants,
}: {
  analytics?: AnalyticsResponse;
  tenants: TenantSummaryResponse[];
}) {
  const [provider, setProvider] = useState<Provider>("openai");
  const [dateWindows, setDateWindows] = useState<Record<DateWindowKey, DateWindow>>({
    summary: DEFAULT_DATE_WINDOW,
    brandAlignment: DEFAULT_DATE_WINDOW,
    health: DEFAULT_DATE_WINDOW,
    ocrTrend: DEFAULT_DATE_WINDOW,
    imageTrend: DEFAULT_DATE_WINDOW,
    llmTokens: DEFAULT_DATE_WINDOW,
    ocrPie: DEFAULT_DATE_WINDOW,
    imagePie: DEFAULT_DATE_WINDOW,
    capacity: { start: "2026-01", end: "2026-02" },
    tenantTokens: DEFAULT_DATE_WINDOW,
  });
  const updateDateWindow = (key: DateWindowKey, value: DateWindow) => {
    setDateWindows((current) => ({
      ...current,
      [key]: normalizeDateWindow(value),
    }));
  };
  const metrics = (analytics?.metrics || {}) as MetricRecord;
  const hasLiveMetrics = Boolean(analytics);
  const summaryTenants = useMemo(() => filterTenantsByWindow(tenants, dateWindows.summary), [tenants, dateWindows.summary]);
  const hasTenantSource = tenants.length > 0;
  const totalTenants = hasTenantSource ? summaryTenants.length : asNumber(metrics.tenants, tenants.length);
  const activeTenants = hasTenantSource
    ? summaryTenants.filter((tenant) => tenant.is_active).length
    : asNumber(metrics.active_tenants, tenants.filter((tenant) => tenant.is_active).length);
  const brandSpaces = hasTenantSource
    ? summaryTenants.reduce((sum, tenant) => sum + asNumber(tenant.brand_space_count), 0)
    : asNumber(metrics.brand_spaces, tenants.reduce((sum, tenant) => sum + asNumber(tenant.brand_space_count), 0));
  const users = hasTenantSource
    ? summaryTenants.reduce((sum, tenant) => sum + asNumber(tenant.total_users), 0)
    : asNumber(metrics.users, tenants.reduce((sum, tenant) => sum + asNumber(tenant.total_users), 0));
  const displayTotalTenants = hasLiveMetrics || summaryTenants.length ? totalTenants : STATIC_METRICS.totalTenants;
  const displayActiveTenants = hasLiveMetrics || summaryTenants.length ? activeTenants : STATIC_METRICS.activeTenants;
  const displayBrandSpaces = hasLiveMetrics || summaryTenants.length ? brandSpaces : STATIC_METRICS.brandSpaces;
  const displayUsers = hasLiveMetrics || summaryTenants.length ? users : STATIC_METRICS.users;
  const topRiskRows = useMemo(() => buildTopRiskRows(tenants), [tenants]);
  const monthlyTokenBars = useMemo(
    () => filterChartByWindow(buildMonthlyTokenBars(analytics, tenants, provider), dateWindows.llmTokens),
    [analytics, tenants, provider, dateWindows.llmTokens],
  );
  const tenantTokenBars = useMemo(
    () => buildTenantTokenBars(filterTenantsByWindow(tenants, dateWindows.tenantTokens), provider, dateWindows.tenantTokens),
    [tenants, provider, dateWindows.tenantTokens],
  );
  const capacityBars = useMemo(
    () => buildCapacityBars(filterTenantsByWindow(tenants, dateWindows.capacity)),
    [tenants, dateWindows.capacity],
  );
  const ocrTrendTenants = useMemo(() => filterTenantsByWindow(tenants, dateWindows.ocrTrend), [tenants, dateWindows.ocrTrend]);
  const imageTrendTenants = useMemo(() => filterTenantsByWindow(tenants, dateWindows.imageTrend), [tenants, dateWindows.imageTrend]);
  const totalOcrPages = ocrTrendTenants.reduce((sum, tenant) => sum + asNumber(tenant.usage_consumption?.ocr_pages), 0);
  const totalImages = imageTrendTenants.reduce((sum, tenant) => sum + asNumber(tenant.usage_consumption?.image_generations), 0);
  const ocrTrend = useMemo(
    () => filterChartByWindow(createSyntheticTrend(totalOcrPages, 120), dateWindows.ocrTrend),
    [totalOcrPages, dateWindows.ocrTrend],
  );
  const imageTrend = useMemo(
    () => filterChartByWindow(createSyntheticTrend(totalImages, 80), dateWindows.imageTrend),
    [totalImages, dateWindows.imageTrend],
  );
  const brandAlignmentTrend = useMemo(
    () => filterChartByWindow(STATIC_BRAND_ALIGNMENT.map((value, index) => ({
      label: MONTHS[index],
      month: monthKeyFromIndex(index),
      value,
    })), dateWindows.brandAlignment),
    [dateWindows.brandAlignment],
  );
  const healthTotalTenants = filterTenantsByWindow(tenants, dateWindows.health).length || displayTotalTenants;
  const healthData = [
    { name: "Health", value: Math.max(1, Math.round(healthTotalTenants * 0.5)), fill: "#DDEEFF" },
    { name: "Need Attention", value: Math.max(1, Math.round(healthTotalTenants * 0.3)), fill: "#FFECA8" },
    { name: "High Risk", value: Math.max(1, Math.round(healthTotalTenants * 0.2)), fill: "#FAD4EC" },
  ];
  const ocrPie = useMemo(
    () => buildTenantPieData(filterTenantsByWindow(tenants, dateWindows.ocrPie), "ocr_pages", !tenants.length),
    [tenants, dateWindows.ocrPie],
  );
  const imagePie = useMemo(
    () => buildTenantPieData(filterTenantsByWindow(tenants, dateWindows.imagePie), "image_generations", !tenants.length),
    [tenants, dateWindows.imagePie],
  );
  const monthlyTokenUsage = totalTokenUsageFromBars(monthlyTokenBars);
  const tenantTokenUsage = totalTokenUsageFromBars(tenantTokenBars);

  return (
    <div className="container">
      <div className="max-w-[1110px] space-y-5">
        <div className="flex items-start justify-between gap-4">
          <h1 className="font-dmSans text-[32px] font-bold leading-none text-primary">Dashboard</h1>
          <DateWindowControl
            value={dateWindows.summary}
            onChange={(value) => updateDateWindow("summary", value)}
          />
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <MetricCard icon={<Grid2X2 />} label="Active Tenants" value={`${displayActiveTenants} / ${displayTotalTenants}`} />
          <MetricCard icon={<Box />} label="Brand Spaces" value={compactNumber(displayBrandSpaces)} />
          <MetricCard icon={<Users />} label="Total Users" value={compactNumber(displayUsers)} />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <MetricCard icon={<Clock3 />} label="Avg Response Time" value={`${STATIC_RESPONSE_TIME_SECONDS} sec`} />
          <MetricCard icon={<BarChart3 />} label="Brand Alignment Score" value={`${STATIC_BRAND_ALIGNMENT_SCORE}%`} />
        </div>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-[#1F2937]">Top Risk Tenants</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="bg-[#F4F5FA] text-[#4B5563]">
                  <th className="px-4 py-3 font-semibold">Tenant Name</th>
                  <th className="px-4 py-3 font-semibold">Brand Alignment</th>
                  <th className="px-4 py-3 font-semibold">Total Capacity Used</th>
                  <th className="px-4 py-3 font-semibold">Brand Spaces</th>
                  <th className="px-4 py-3 font-semibold">Active (Last 30 Days)</th>
                </tr>
              </thead>
              <tbody>
                {topRiskRows.map((tenant) => (
                  <tr key={tenant.id} className="border-t border-white bg-[#F7F8FC] text-[#6B7280]">
                    <td className="px-4 py-3">{tenant.name}</td>
                    <td className="px-4 py-3">{tenant.alignment}%</td>
                    <td className="px-4 py-3">{tenant.capacity}%</td>
                    <td className="px-4 py-3">{tenant.brandSpaces}</td>
                    <td className="px-4 py-3">{tenant.activity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <div className="grid gap-5 lg:grid-cols-2">
          <DashboardCard
            title="Brand Alignment"
            toolbar={
              <DateWindowControl
                value={dateWindows.brandAlignment}
                onChange={(value) => updateDateWindow("brandAlignment", value)}
              />
            }
          >
            <PercentAreaChart data={brandAlignmentTrend} />
          </DashboardCard>
          <DashboardCard
            title="Tenant Health Overview"
            toolbar={
              <DateWindowControl
                value={dateWindows.health}
                onChange={(value) => updateDateWindow("health", value)}
              />
            }
          >
            <div className="grid min-h-[240px] grid-cols-[1fr_160px] items-center gap-3">
              <DonutHealthChart data={healthData} total={healthTotalTenants} />
              <LegendList data={healthData} />
            </div>
          </DashboardCard>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <DashboardCard
            title="Total OCR Pages"
            toolbar={
              <DateWindowControl
                value={dateWindows.ocrTrend}
                onChange={(value) => updateDateWindow("ocrTrend", value)}
              />
            }
          >
            <SoftAreaChart data={ocrTrend} />
          </DashboardCard>
          <DashboardCard
            title="Total Images Generated"
            toolbar={
              <DateWindowControl
                value={dateWindows.imageTrend}
                onChange={(value) => updateDateWindow("imageTrend", value)}
              />
            }
          >
            <SoftAreaChart data={imageTrend} />
          </DashboardCard>
        </div>

        <DashboardCard
          title="LLM Tokens"
          toolbar={
            <DateWindowControl
              value={dateWindows.llmTokens}
              onChange={(value) => updateDateWindow("llmTokens", value)}
            />
          }
          className="min-h-[430px]"
        >
          <ProviderToggle provider={provider} onChange={setProvider} />
          <TokenTotals tokenUsage={monthlyTokenUsage} />
          <GroupedBarChart data={monthlyTokenBars} />
        </DashboardCard>

        <div className="grid gap-5 lg:grid-cols-2">
          <DashboardCard
            title="OCR Usage per Tenant"
            toolbar={
              <DateWindowControl
                value={dateWindows.ocrPie}
                onChange={(value) => updateDateWindow("ocrPie", value)}
              />
            }
          >
            <TenantPieChart data={ocrPie} />
          </DashboardCard>
          <DashboardCard
            title="Images Generated per Tenant"
            toolbar={
              <DateWindowControl
                value={dateWindows.imagePie}
                onChange={(value) => updateDateWindow("imagePie", value)}
              />
            }
          >
            <TenantPieChart data={imagePie} />
          </DashboardCard>
        </div>

        <DashboardCard
          title="Capacity Usage per Tenant"
          toolbar={
            <div className="flex gap-3">
              <SmallSelectLabel label="Total Capacity" />
              <DateWindowControl
                value={dateWindows.capacity}
                defaultValue={{ start: "2026-01", end: "2026-02" }}
                onChange={(value) => updateDateWindow("capacity", value)}
              />
            </div>
          }
          className="min-h-[410px]"
        >
          <CapacityBarChart data={capacityBars} />
        </DashboardCard>

        <DashboardCard
          title="LLM Tokens per Tenant"
          toolbar={
            <DateWindowControl
              value={dateWindows.tenantTokens}
              onChange={(value) => updateDateWindow("tenantTokens", value)}
            />
          }
          className="min-h-[430px]"
        >
          <ProviderToggle provider={provider} onChange={setProvider} />
          <TokenTotals tokenUsage={tenantTokenUsage} label="LLM Tokens" />
          <GroupedBarChart data={tenantTokenBars} />
        </DashboardCard>
      </div>
    </div>
  );
}

function MetricCard({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="flex min-h-[90px] items-start gap-4 border border-[#E4E7EC] bg-white px-5 py-4">
      <div className="flex h-11 w-11 items-center justify-center bg-[#F7F7FB] text-[#6B7280] [&_svg]:h-5 [&_svg]:w-5">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium text-[#6B7280]">{label}</p>
        <p className="mt-3 text-2xl font-semibold leading-none text-[#111827]">{value}</p>
      </div>
    </div>
  );
}

function DashboardCard({
  title,
  toolbar,
  children,
  className,
}: {
  title: string;
  toolbar?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`border border-[#E4E7EC] bg-white p-5 ${className || ""}`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <h2 className="text-base font-semibold text-[#344054]">{title}</h2>
        {toolbar}
      </div>
      {children}
    </section>
  );
}

function DateWindowControl({
  value,
  defaultValue = DEFAULT_DATE_WINDOW,
  onChange,
}: {
  value: DateWindow;
  defaultValue?: DateWindow;
  onChange: (value: DateWindow) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const normalized = normalizeDateWindow(value);

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="inline-flex h-12 shrink-0 items-center gap-3 border border-[#D5D8E8] bg-white px-5 text-base font-medium text-[#1F2937] shadow-none transition hover:bg-[#FAFAFD]"
        >
          <CalendarDays className="h-5 w-5 text-[#344054]" />
          <span>{formatDateWindow(normalized)}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        sideOffset={6}
        className="w-[400px] rounded-[10px] border border-[#D5D8E8] bg-white p-5 text-[#2F3342] shadow-[0_18px_48px_-20px_rgba(15,23,42,0.35)]"
      >
        <div className="space-y-5">
          <div>
            <p className="text-lg font-semibold leading-6 text-[#2F3342]">Usage window</p>
            <p className="mt-1 text-base leading-5 text-[#6B7280]">
              Choose the month range to display in the chart and table.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <MonthField
              label="Start Month"
              value={normalized.start}
              onChange={(nextValue) => onChange({ ...normalized, start: nextValue })}
            />
            <MonthField
              label="End Month"
              value={normalized.end}
              onChange={(nextValue) => onChange({ ...normalized, end: nextValue })}
            />
          </div>
          <div className="flex items-center justify-between border-t border-[#E4E7EC] pt-4">
            <p className="text-sm font-medium text-[#6B7280]">{formatDateWindow(normalized)}</p>
            <button
              type="button"
              onClick={() => onChange(defaultValue)}
              className="text-sm font-semibold text-primary transition hover:text-primary/80"
            >
              Reset window
            </button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

function MonthField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="space-y-2">
      <span className="block text-base font-medium text-[#666666]">{label}</span>
      <span className="relative block">
        <input
          type="month"
          value={value}
          min="2020-01"
          max="2030-12"
          onChange={(event) => onChange(event.target.value || value)}
          className="h-[50px] w-full rounded-[8px] border border-[#BDB5EF] bg-white px-4 pr-10 text-lg text-[#344054] outline-none transition focus:border-primary focus:ring-1 focus:ring-primary"
        />
        <CalendarDays className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[#111827]" />
      </span>
    </label>
  );
}

function SmallSelectLabel({ label }: { label: string }) {
  return (
    <div className="inline-flex h-10 items-center gap-2 border border-[#D5D8E8] bg-white px-3 text-sm font-medium text-[#667085]">
      <BarChart3 className="h-4 w-4" />
      <span>{label}</span>
      <ChevronDown className="h-3 w-3" />
    </div>
  );
}

function PercentAreaChart({ data }: { data: ChartPoint[] }) {
  return (
    <div className="h-[230px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -22 }}>
          <CartesianGrid vertical={false} stroke="#EEF1F6" />
          <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#667085" }} />
          <YAxis
            tickFormatter={(value) => `${value}%`}
            ticks={[0, 10, 25, 50, 75, 100]}
            domain={[0, 100]}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 11, fill: "#667085" }}
          />
          <Tooltip formatter={(value) => [`${value}%`, "Brand alignment"]} />
          <Area type="monotone" dataKey="value" stroke="#8C8F94" fill="#ECECEC" strokeWidth={2} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function SoftAreaChart({ data }: { data: ChartPoint[] }) {
  return (
    <div className="h-[230px]">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid vertical={false} stroke="#F0F2F6" />
          <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#667085" }} />
          <YAxis hide />
          <Tooltip />
          <Area type="monotone" dataKey="value" stroke="#8C8F94" fill="#F0F0F0" strokeWidth={2} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function DonutHealthChart({ data, total }: { data: Array<{ name: string; value: number; fill: string }>; total: number }) {
  return (
    <div className="relative h-[220px]">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="value" innerRadius={56} outerRadius={92} paddingAngle={0} stroke="none">
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <div className="text-center text-xs text-[#667085]">
          <p>Total Tenant</p>
          <p className="text-lg font-semibold text-[#111827]">{total}</p>
        </div>
      </div>
    </div>
  );
}

function LegendList({ data }: { data: Array<{ name: string; value: number; fill: string }> }) {
  const total = data.reduce((sum, item) => sum + item.value, 0) || 1;
  return (
    <div className="space-y-3 bg-[#FAFAFC] p-3">
      {data.map((item) => (
        <div key={item.name} className="flex items-start gap-3 text-xs text-[#667085]">
          <span className="mt-1 h-4 w-4" style={{ backgroundColor: item.fill }} />
          <span>
            {item.name}
            <br />
            {Math.round((item.value / total) * 100)}%
          </span>
        </div>
      ))}
    </div>
  );
}

function ProviderToggle({
  provider,
  onChange,
}: {
  provider: "openai" | "anthropic";
  onChange: (provider: "openai" | "anthropic") => void;
}) {
  return (
    <div className="mb-5 flex justify-center gap-3">
      <button
        type="button"
        onClick={() => onChange("openai")}
        className={`h-9 border px-4 text-sm ${provider === "openai" ? "bg-white text-[#344054]" : "bg-[#F3F4F7] text-[#667085]"}`}
      >
        OpenAI
      </button>
      <button
        type="button"
        onClick={() => onChange("anthropic")}
        className={`h-9 border px-4 text-sm ${provider === "anthropic" ? "bg-[#D6D6DD] text-[#344054]" : "bg-white text-[#667085]"}`}
      >
        Anthropic
      </button>
    </div>
  );
}

function TokenTotals({ tokenUsage, label }: { tokenUsage: TokenUsage; label?: string }) {
  return (
    <div className="mb-3 pl-6 text-sm text-[#344054]">
      {label ? <p className="font-semibold">{label}</p> : null}
      <p className="text-lg font-semibold">{compactNumber(asNumber(tokenUsage.total_tokens))}</p>
      <p className="text-xs font-semibold text-[#667085]">{compactNumber(asNumber(tokenUsage.input_tokens))}</p>
      <div className="mt-2 space-y-1 text-xs text-[#667085]">
        <LegendDot color="#A3A6B3" label="Input Tokens" />
        <LegendDot color="#4A4A4A" label="Output Tokens" />
      </div>
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="inline-flex items-center gap-2 pr-4">
      <span className="h-3 w-3" style={{ backgroundColor: color }} />
      <span>{label}</span>
    </div>
  );
}

function GroupedBarChart({ data }: { data: ChartPoint[] }) {
  return (
    <div className="h-[240px]">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="#EDF0F5" />
          <XAxis dataKey="label" tickLine={false} axisLine={false} interval={0} tick={{ fontSize: 11, fill: "#667085" }} />
          <YAxis hide />
          <Tooltip />
          <Bar dataKey="output" fill="#4A4A4A" barSize={8} />
          <Bar dataKey="input" fill="#A3A6B3" barSize={8} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function TenantPieChart({ data }: { data: Array<{ name: string; value: number; fill: string }> }) {
  return (
    <div className="grid min-h-[250px] grid-cols-[1fr_180px] items-center gap-3">
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Tooltip formatter={(value, name) => [`${value}`, name]} />
          <Pie data={data} dataKey="value" nameKey="name" outerRadius={88} stroke="none">
            {data.map((entry) => (
              <Cell key={entry.name} fill={entry.fill} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="max-h-[190px] space-y-2 overflow-y-auto pr-2">
        {data.map((item) => (
          <div key={item.name} className="flex items-center gap-2 text-xs text-[#667085]">
            <span className="h-4 w-4" style={{ backgroundColor: item.fill }} />
            <span className="truncate">{item.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CapacityBarChart({ data }: { data: ChartPoint[] }) {
  return (
    <div className="h-[300px] pt-3">
      <div className="mb-3 flex gap-5 pl-5 text-xs text-[#667085]">
        <LegendDot color="#C6C6C6" label="Total Capacity" />
        <LegendDot color="#4A4A4A" label="Capacity Used" />
      </div>
      <ResponsiveContainer width="100%" height="85%">
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="#EDF0F5" />
          <XAxis dataKey="label" tickLine={false} axisLine={false} interval={0} tick={{ fontSize: 11, fill: "#667085" }} />
          <YAxis hide domain={[0, 100]} />
          <Tooltip formatter={(value) => [`${value}%`, "Capacity"]} />
          <Bar dataKey="total" fill="#C6C6C6" barSize={10} />
          <Bar dataKey="used" fill="#4A4A4A" barSize={10} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
