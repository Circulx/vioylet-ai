"use client";

import { useMemo } from "react";
import { useParams, useSearchParams } from "next/navigation";
import BrandSpaceEditor from "@/components/brandSpaces/BrandSpaceEditor";
import WorkspaceChat from "@/components/chat/WorkspaceChat";
import { useBrandOverview, useBrands } from "@/hooks/useBrands";
import { mapBrandOverviewToForm } from "@/lib/brand-mappers";
import { resolveBrandByRouteKey } from "@/lib/brand-routing";

export default function BrandWorkspacePage() {
  const params = useParams<{ brandSlug: string }>();
  const searchParams = useSearchParams();
  const chatId = searchParams.get("chat");
  const { data: brands, isLoading: isBrandsLoading } = useBrands();
  const brand = useMemo(
    () => resolveBrandByRouteKey(brands, params.brandSlug),
    [brands, params.brandSlug],
  );
  const { data: overview, isLoading: isOverviewLoading } = useBrandOverview(brand?.id || "");

  const initialForm = useMemo(
    () => (overview ? mapBrandOverviewToForm(overview) : undefined),
    [overview],
  );

  if (isBrandsLoading || isOverviewLoading || !brand || !overview || !initialForm) {
    return <div className="w-full px-6 py-10 text-sm text-slate-500">Loading Brand Space...</div>;
  }

  if (chatId) {
    return <WorkspaceChat brandKey={params.brandSlug} />;
  }

  return (
    <BrandSpaceEditor
      mode="edit"
      brandId={brand.id}
      initialForm={initialForm}
      initialLifecycleState={overview.brand.lifecycle_state}
    />
  );
}
