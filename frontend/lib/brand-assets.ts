import type { BrandResponse } from "@/lib/api/contracts";
import { apiOrigin } from "@/lib/env";

type AnyBrand = BrandResponse & {
  logo?: string | null;
};

function resolveStorageUrl(value: string) {
  if (/^https?:\/\//i.test(value) || value.startsWith("/")) {
    return value;
  }
  return `${apiOrigin}/storage/${value}`;
}

export function resolveBrandLogoUrl(brand: AnyBrand): string | null {
  if ("logo" in brand && typeof brand.logo === "string" && brand.logo) {
    return resolveStorageUrl(brand.logo);
  }

  if (!("resolved_brand_context" in brand)) {
    return null;
  }

  const identity = (brand.resolved_brand_context as Record<string, unknown>)?.identity as
    | Record<string, unknown>
    | undefined;

  const storagePath = identity?.logo_asset_path;
  if (typeof storagePath === "string" && storagePath) {
    return resolveStorageUrl(storagePath);
  }

  const logoAssets = identity?.logo_assets;
  if (Array.isArray(logoAssets)) {
    const firstLogoPath = logoAssets
      .map((asset) => (asset && typeof asset === "object" ? (asset as Record<string, unknown>).storage_path : undefined))
      .find((value): value is string => typeof value === "string" && Boolean(value));
    if (firstLogoPath) {
      return resolveStorageUrl(firstLogoPath);
    }
  }

  const directUrl = identity?.logo_asset_url;
  if (typeof directUrl === "string" && directUrl) {
    return directUrl;
  }

  return null;
}
