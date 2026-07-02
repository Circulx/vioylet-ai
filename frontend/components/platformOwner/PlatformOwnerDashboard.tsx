"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { DonutChart, Sparkline } from "@/components/common/DesignPrimitives";
import {
  DatePill,
  MetricTile,
  PlatformPageTitle,
  PlatformTabSwitcher,
  SectionCard,
  SimpleBarChart,
  ToolbarToggle,
} from "@/components/platformOwner/PlatformOwnerPrimitives";
import type { AnalyticsResponse, TenantSummaryResponse } from "@/lib/api/contracts";
import {
  buildPlatformMetricCards,
  formatMonthLabel,
  buildRangeLabel,
  buildTenantBreakdownRows,
  buildTenantUsageSeries,
  formatShortDate,
  getActivityLabel,
} from "@/lib/platform-owner";

export default function PlatformOwnerDashboard({
  analytics,
  tenants,
}: {
  analytics?: AnalyticsResponse;
  tenants: TenantSummaryResponse[];
}) {
  const router = useRouter();
  const [dashboardTab, setDashboardTab] = useState("platform");
  const [provider, setProvider] = useState("openai");
  const metrics = useMemo(() => buildPlatformMetricCards(analytics), [analytics]);
  const tenantRows = useMemo(() => buildTenantBreakdownRows(tenants), [tenants]);
  const usageSeries = useMemo(() => buildTenantUsageSeries(tenants).slice(0, 10), [tenants]);
  const dateLabel = useMemo(() => {
    const firstTenant = tenants[0];
    const usageWindow = firstTenant?.metadata_json?.usage_window as Record<string, unknown> | undefined;
    return buildRangeLabel(
      typeof usageWindow?.start_month === "string" ? usageWindow.start_month : undefined,
      typeof usageWindow?.end_month === "string" ? usageWindow.end_month : undefined,
    );
  }, [tenants]);

  const monthlyBars = useMemo(() => {
    const tokenUsage = analytics?.metrics?.token_usage as
      | {
          monthly_token_usage?: Array<{ month: string; input_tokens: number; output_tokens: number }>;
        }
      | undefined;
    const monthlyUsage = tokenUsage?.monthly_token_usage || [];
    if (monthlyUsage.length) {
      return monthlyUsage.map((item) => ({
        label: formatMonthLabel(item.month).split(" ")[0],
        primary: item.input_tokens,
        secondary: item.output_tokens,
      }));
    }
    return [];
  }, [analytics?.metrics]);

  const ocrTrend = useMemo(
    () => usageSeries.map((item) => item.ocr).slice(0, 8),
    [usageSeries],
  );
  const visualTrend = useMemo(
    () => usageSeries.map((item) => item.visual).slice(0, 8),
    [usageSeries],
  );

  const usageSegments = useMemo(
    () =>
      usageSeries.map((item, index) => ({
        name: item.label,
        color: ["#F7C5EA", "#DDEEFF", "#F6E3A3", "#B9F2D0", "#DCC7FF", "#F4CFA7"][index % 6],
        value: item.ocr,
      })),
    [usageSeries],
  );

  const visualSegments = useMemo(
    () =>
      usageSeries.map((item, index) => ({
        name: item.label,
        color: ["#F7C5EA", "#DDEEFF", "#F6E3A3", "#B9F2D0", "#DCC7FF", "#F4CFA7"][index % 6],
        value: item.visual,
      })),
    [usageSeries],
  );

  return (
    <div className="container">
      <div className="max-w-[1110px] space-y-6">
        <PlatformPageTitle
          title="Dashboard"
          action={
            <Button
              onClick={() => router.push("/tenants/create")}
              className="h-12 rounded-[2px] bg-[#8F8F97] px-6 text-base font-semibold hover:bg-[#777782]"
            >
              Create Tenant
            </Button>
          }
        >
          <PlatformTabSwitcher
            tabs={[
              { id: "platform", label: "Platform" },
              { id: "tenant", label: "Tenant" },
            ]}
            active={dashboardTab}
            onChange={setDashboardTab}
          />
        </PlatformPageTitle>

        {dashboardTab === "platform" ? (
          <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-5">
              {metrics.map((metric) => (
                <MetricTile key={metric.label} label={metric.label} value={metric.value} />
              ))}
            </div>

            <SectionCard
              title="LLM Tokens"
              toolbar={
                <div className="flex items-center gap-3">
                  <ToolbarToggle
                    items={[
                      { id: "openai", label: "OpenAI" },
                      { id: "anthropic", label: "Anthropic" },
                    ]}
                    active={provider}
                    onChange={setProvider}
                  />
                  <DatePill label={dateLabel} />
                </div>
              }
            >
              <div className="mb-3 flex items-center gap-5 text-[11px] text-[#6B7280]">
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-[#A3A6B3]" />
                  Input Tokens
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-[#3D414E]" />
                  Output Tokens
                </span>
              </div>
              <SimpleBarChart data={monthlyBars} />
            </SectionCard>

            <div className="grid gap-4 xl:grid-cols-2">
              <SectionCard title="Total OCR Pages" toolbar={<DatePill label={dateLabel} />}>
                <Sparkline values={ocrTrend.length ? ocrTrend : [1, 2, 3, 2, 4, 5]} />
              </SectionCard>
              <SectionCard title="Total Images Generated" toolbar={<DatePill label={dateLabel} />}>
                <Sparkline values={visualTrend.length ? visualTrend : [1, 3, 2, 4, 4, 5]} />
              </SectionCard>
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <SectionCard
              title="LLM Tokens per Tenant"
              toolbar={
                <div className="flex items-center gap-3">
                  <ToolbarToggle
                    items={[
                      { id: "openai", label: "OpenAI" },
                      { id: "anthropic", label: "Anthropic" },
                    ]}
                    active={provider}
                    onChange={setProvider}
                  />
                  <DatePill label={dateLabel} />
                </div>
              }
            >
              <div className="mb-3 flex items-center gap-5 text-[11px] text-[#6B7280]">
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-[#A3A6B3]" />
                  Input Tokens
                </span>
                <span className="inline-flex items-center gap-1">
                  <span className="inline-block h-2 w-2 rounded-full bg-[#3D414E]" />
                  Output Tokens
                </span>
              </div>
              <SimpleBarChart
                data={
                  usageSeries
                    .filter((item) => item.inputTokens || item.outputTokens)
                    .map((item) => ({
                      label: item.label.slice(0, 3),
                      primary: item.inputTokens || 0,
                      secondary: item.outputTokens || 0,
                    }))
                }
              />
            </SectionCard>

            <div className="grid gap-4 xl:grid-cols-2">
              <SectionCard title="OCR Usage per Tenant" toolbar={<DatePill label={dateLabel} />}>
                <DonutChart segments={usageSegments.length ? usageSegments : [{ name: "No data", value: 1, color: "#DDEEFF" }]} />
              </SectionCard>
              <SectionCard title="Images Generated per Tenant" toolbar={<DatePill label={dateLabel} />}>
                <DonutChart segments={visualSegments.length ? visualSegments : [{ name: "No data", value: 1, color: "#DDEEFF" }]} />
              </SectionCard>
            </div>

            <SectionCard
              title="Capacity Usage per Tenant"
              toolbar={
                <div className="flex items-center gap-3">
                  <ToolbarToggle items={[{ id: "capacity", label: "Total Capacity" }]} active="capacity" onChange={() => undefined} />
                  <DatePill label={dateLabel} />
                </div>
              }
            >
              <SimpleBarChart
                data={usageSeries.map((item) => ({
                  label: item.label.slice(0, 3),
                  primary: item.total,
                  secondary: 0,
                }))}
                tone="stack"
              />
            </SectionCard>

            <SectionCard title="Top 5 by Capacity">
              <div className="overflow-x-auto">
                <table className="table">
                  <thead className="border-b border-[#ECEEF5] text-[#6B7280]">
                    <tr className="bg-slate-100/50 text-black">
                      <th className="pb-3 font-medium">Tenant Name</th>
                      <th className="pb-3 font-medium">Date Created</th>
                      <th className="pb-3 font-medium">Total Capacity Used</th>
                      <th className="pb-3 font-medium">Brand Spaces</th>
                      <th className="pb-3 font-medium">Active (Last 30 Days)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tenantRows
                      .sort((left, right) => right.capacityUsed - left.capacityUsed)
                      .slice(0, 5)
                      .map((tenant) => (
                        <tr key={tenant.id} className="border-b border-[#F1F2F6] text-[#4B5563]">
                          <td className="py-3">{tenant.name}</td>
                          <td className="py-3">{formatShortDate(tenant.createdAt)}</td>
                          <td className="py-3">{tenant.capacityUsed}%</td>
                          <td className="py-3">{tenant.brandSpaces}</td>
                          <td className="py-3">{getActivityLabel(tenant.activeDate)}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>
          </div>
        )}
      </div>
    </div>
  );
}
