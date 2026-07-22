// lib/sidebarItems.ts

import type { Module } from "@/types/rbac.types";

export type SidebarItemProps = {
  id: number;
  name: string;
  href?: string;
  icon: string;
  module: Module;
};

export const sidebarItems: SidebarItemProps[] = [
  {
    id: 1,
    name: "Tenant Management",
    href: "/tenants",
    icon: "/box",
    module: "TENANT_MANAGEMENT",
  },
  {
    id: 2,
    name: "Brand Spaces",
    href: "/brand_space",
    icon: "/box",
    module: "BRAND_SPACE",
  },
  {
    id: 3,
    name: "Dashboard",
    href: "/dashboard",
    icon: "/dashboard",
    module: "DASHBOARD",
  },
  {
    id: 5,
    name: "User Management",
    href: "/user_management",
    icon: "/user_management",
    module: "USER_MANAGEMENT",
  },
  {
    id: 6,
    name: "Notification",
    icon: "/notification",
    module: "NOTIFICATION",
  },
];
