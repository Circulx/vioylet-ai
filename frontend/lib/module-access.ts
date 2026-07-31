import type { Module, Role } from "@/types/rbac.types";

export const ROLE_MODULES: Record<Role, Module[]> = {
  PLATFORM_OWNER: ["TENANT_MANAGEMENT", "DASHBOARD", "NOTIFICATION"],

  TENANT_ADMIN: [
    "BRAND_SPACE",
    "DASHBOARD",
    "USER_MANAGEMENT",
    "NOTIFICATION",
  ],

  TENANT_USER: [
    "BRAND_SPACE",
    "DASHBOARD",
    // "USER_MANAGEMENT",
    "NOTIFICATION",
  ],

  BRAND_USER: [
    "BRAND_SPACE",
    "NOTIFICATION",
  ],
};
