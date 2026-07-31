import { ROLE_MODULES } from "@/lib/module-access";
import type { Module, Role } from "@/types/rbac.types";

const ROLE_DEFAULT_PATHS: Record<Role, string> = {
  PLATFORM_OWNER: "/tenants",
  TENANT_ADMIN: "/brand_space",
  TENANT_USER: "/brand_space",
  BRAND_USER: "/brand_space",
};

const ROUTE_MODULES: Array<{ path: string; module: Module }> = [
  { path: "/tenants", module: "TENANT_MANAGEMENT" },
  { path: "/brand_space", module: "BRAND_SPACE" },
  { path: "/dashboard", module: "DASHBOARD" },
  { path: "/analytics", module: "ANALYTICS" },
  { path: "/user_management", module: "USER_MANAGEMENT" },
];

export function roleFromRoleCodes(roleCodes: string[]): Role {
  if (roleCodes.includes("super_admin")) {
    return "PLATFORM_OWNER";
  }
  if (roleCodes.includes("tenant_admin")) {
    return "TENANT_ADMIN";
  }
  if (roleCodes.includes("tenant_user")) {
    return "TENANT_USER";
  }
  return "BRAND_USER";
}

export function defaultPathForRole(role: Role) {
  return ROLE_DEFAULT_PATHS[role];
}

export function defaultPathForRoleCodes(roleCodes: string[]) {
  return defaultPathForRole(roleFromRoleCodes(roleCodes));
}

export function moduleForPath(pathname: string) {
  return ROUTE_MODULES.find((entry) => pathname === entry.path || pathname.startsWith(`${entry.path}/`))?.module || null;
}

export function canAccessPath(role: Role, pathname: string) {
  const module = moduleForPath(pathname);
  if (!module) {
    return true;
  }
  return ROLE_MODULES[role]?.includes(module) ?? false;
}

export function safeAppRedirectForRole(role: Role, requestedPath: string | null | undefined) {
  const fallbackPath = defaultPathForRole(role);
  if (!requestedPath || !requestedPath.startsWith("/") || requestedPath.startsWith("//")) {
    return fallbackPath;
  }
  return canAccessPath(role, requestedPath) ? requestedPath : fallbackPath;
}
