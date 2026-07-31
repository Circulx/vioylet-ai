"use client";

import { useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import BrandSpaceEditor from "@/components/brandSpaces/BrandSpaceEditor";
import { useBrandOverview, useBrands } from "@/hooks/useBrands";
import { useRBAC } from "@/hooks/useRBAC";
import { mapBrandOverviewToForm } from "@/lib/brand-mappers";
import { buildBrandViewHref, resolveBrandByRouteKey } from "@/lib/brand-routing";

export default function EditBrandSpacePage() {
  const params = useParams<{ brandSlug: string }>();
  const router = useRouter();
  const { user, can } = useRBAC();
  const { data: brands, isLoading: isBrandsLoading } = useBrands();
  const brand = useMemo(
    () => resolveBrandByRouteKey(brands, params.brandSlug),
    [brands, params.brandSlug],
  );
  const { data: overview, isLoading: isOverviewLoading } = useBrandOverview(brand?.id || "");
  const canEditBrandSpace = Boolean(user && can("BRAND_SPACE", "EDIT"));

  const initialForm = useMemo(
    () => (overview ? mapBrandOverviewToForm(overview) : undefined),
    [overview],
  );

  useEffect(() => {
    if (!user || !brand || canEditBrandSpace) {
      return;
    }
    router.replace(buildBrandViewHref(brand));
  }, [brand, canEditBrandSpace, router, user]);

  if (user && brand && !canEditBrandSpace) {
    return <div className="w-full px-6 py-10 text-sm text-slate-500">Opening read-only Brand Space...</div>;
  }

  if (isBrandsLoading || isOverviewLoading || !brand || !overview || !initialForm) {
    return <div className="w-full px-6 py-10 text-sm text-slate-500">Loading Brand Space...</div>;
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
