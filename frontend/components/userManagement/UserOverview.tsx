"use client";

import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { FormField, FormSubsection, StyledInput } from "@/components/brandSpaces/tabs/FormFields";
import { PlatformPageTitle } from "@/components/platformOwner/PlatformOwnerPrimitives";
import { resolveBrandLogoUrl } from "@/lib/brand-assets";
import { buildBrandWorkspaceHref } from "@/lib/brand-routing";
import { useBrands } from "@/hooks/useBrands";
import { getTenantUserRequestId, useTenantUserDetail } from "@/hooks/useTeamAccess";

type AssignedBrand = {
  id: string;
  slug: string;
  name: string;
  logo: string | null;
};

export default function UserOverview({ userId }: { userId: string }) {
  const { data: liveUser, isLoading } = useTenantUserDetail(userId);
  const { data: brands } = useBrands();
  const detailUserId = getTenantUserRequestId(liveUser) || userId;

  const user = liveUser
    ? {
        fullName: liveUser.full_name,
        email: liveUser.email,
        contactNumber: liveUser.phone_number || "",
        role: liveUser.role_codes.includes("tenant_admin")
          ? "Tenant Admin"
          : liveUser.role_codes.includes("tenant_user")
            ? "Tenant User"
            : "Brand User",
        brandAssignments: liveUser.brand_space_ids.map((brandId) => {
          const brand = (brands || []).find((item) => item.id === brandId);
          return {
            id: brandId,
            slug: brand?.slug || brandId,
            name: brand?.name || brandId,
            logo: brand ? resolveBrandLogoUrl(brand) : null,
          };
        }) satisfies AssignedBrand[],
      }
    : null;

  if (!user && isLoading) {
    return <div className="w-full px-6 py-10 text-sm text-slate-500">Loading user details...</div>;
  }

  if (!user) {
    return <div className="w-full px-6 py-10 text-sm text-slate-500">User not found.</div>;
  }

  const isBrandUser = user.role === "Brand User";

  return (
    <div className="w-full px-4 py-6">
                <div className="mx-auto ">
        <PlatformPageTitle
          title={`${user.fullName || (isBrandUser ? "{Brand user name}" : "{Tenant User name}")} Overview`}
          action={
          <Button asChild className="rounded-none bg-primary/72 px-8 py-5 text-base hover:bg-primary/90">
            <Link href={`/user_management/${detailUserId}?edit=true`}>Edit</Link>
          </Button>
        }
        />

        <FormSubsection >
          <div className="max-w-[458px] space-y-5">
            <FormField label="Full Name" required>
              <StyledInput value={user.fullName} readOnly />
            </FormField>

            <FormField label="Email Address" required>
              <StyledInput value={user.email} readOnly />
            </FormField>

            <FormField label="Contact Number" required>
              <StyledInput value={user.contactNumber} readOnly />
            </FormField>

            <FormField label="User Role" required>
              <StyledInput value={user.role} readOnly />
            </FormField>
          </div>
        </FormSubsection>

        {isBrandUser ? (
          <section className="space-y-3 mt-6">
            <h1 className="pb-4">Brand Spaces Assigned</h1>
            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6 border p-4">
              {user.brandAssignments.map((brand) => (
                <Link
                  key={brand.id}
                  href={buildBrandWorkspaceHref(brand)}
                  className="flex min-h-[104px] flex-col items-center justify-center gap-3 rounded-[2px] border border-[#D8D1FF] bg-[#FAFBFF] p-4 transition hover:border-primary focus-visible:border-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary"
                >
                  {brand.logo ? (
                    <div className="relative h-16 w-32 overflow-hidden">
                      <Image src={brand.logo} alt={brand.name} fill sizes="128px" className="scale-[1.65] object-contain" unoptimized />
                    </div>
                  ) : (
                    <span className="text-sm font-semibold text-slate-700">{brand.name}</span>
                  )}
                </Link>
              ))}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}
