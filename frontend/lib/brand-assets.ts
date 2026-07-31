import type { BrandResponse } from "@/lib/api/contracts";
import { apiOrigin } from "@/lib/env";

type AnyBrand = BrandResponse & {
  logo?: string | null;
  logo_url?: string | null;
};

function resolveStorageUrl(value: string) {
  if (/^https?:\/\//i.test(value) || value.startsWith("/")) {
    return value;
  }
  return `${apiOrigin}/storage/${value}`;
}

function firstString(...values: unknown[]) {
  return values.find((value): value is string => typeof value === "string" && Boolean(value.trim())) || null;
}

function resolveLogoAssetUrl(asset: unknown) {
  if (!asset || typeof asset !== "object") {
    return null;
  }

  const record = asset as Record<string, unknown>;
  const directUrl = firstString(
    record.asset_url,
    record.assetUrl,
    record.url,
    record.preview_url,
    record.previewUrl,
  );
  if (directUrl) {
    return resolveStorageUrl(directUrl);
  }

  const storagePath = firstString(record.storage_path, record.storagePath, record.path);
  return storagePath ? resolveStorageUrl(storagePath) : null;
}

export function resolveBrandLogoUrl(brand: AnyBrand): string | null {
  const directBrandUrl = firstString(brand.logo_url, brand.logo);
  if (directBrandUrl) {
    return resolveStorageUrl(directBrandUrl);
  }

  if (!("resolved_brand_context" in brand)) {
    return null;
  }

  const identity = (brand.resolved_brand_context as Record<string, unknown>)?.identity as
    | Record<string, unknown>
    | undefined;

  const directUrl = firstString(identity?.logo_asset_url, identity?.logoAssetUrl);
  if (directUrl) {
    return resolveStorageUrl(directUrl);
  }

  const logoAssets = identity?.logo_assets;
  if (Array.isArray(logoAssets)) {
    const firstLogoUrl = logoAssets.map(resolveLogoAssetUrl).find((value): value is string => Boolean(value));
    if (firstLogoUrl) {
      return firstLogoUrl;
    }
  }

  const storagePath = firstString(identity?.logo_asset_path, identity?.logoAssetPath);
  if (storagePath) {
    return resolveStorageUrl(storagePath);
  }

  return null;
}
