import { useMemo } from "react";
import { useCreateTenantUser } from "@/hooks/tenantAdmins/useCreateTenant";
import { useGetTenantUser, useGetTenantUsers } from "@/hooks/tenantAdmins/useGetTenants";
import { useUpdateTenantUser } from "@/hooks/tenantAdmins/useUpdateTenant";
import { useGetMe } from "@/hooks/useUser";
import type { TenantUserResponse } from "@/lib/api/contracts";

const SUPER_USER_ROLE_CODE = "tenant_user";
const BRAND_USER_ROLE_CODE = "brand_user";
const TEAM_ACCESS_ROLE_CODES = [SUPER_USER_ROLE_CODE, BRAND_USER_ROLE_CODE];
const TEAM_ACCESS_EXCLUDED_ROLE_CODES = ["tenant_admin"];
const ASSIGNABLE_USER_ROLE_CODES = [...TEAM_ACCESS_ROLE_CODES, ...TEAM_ACCESS_EXCLUDED_ROLE_CODES];

function hasOnlyAssignableRole(user: TenantUserResponse, roleCode: string) {
  return (
    user.role_codes.includes(roleCode) &&
    ASSIGNABLE_USER_ROLE_CODES.every((assignableRoleCode) => {
      return assignableRoleCode === roleCode || !user.role_codes.includes(assignableRoleCode);
    })
  );
}

export function getTenantUserRequestId(user?: TenantUserResponse | null) {
  return user?.user_id || user?.id || "";
}

export const useTenantUsers = () => {
  const { data: currentUser } = useGetMe();
  const tenantId = currentUser?.tenantId || "";
  const query = useGetTenantUsers(tenantId, TEAM_ACCESS_ROLE_CODES, TEAM_ACCESS_EXCLUDED_ROLE_CODES);
  const tenantUsers = useMemo(
    () => (query.data || []).filter((user) => hasOnlyAssignableRole(user, SUPER_USER_ROLE_CODE)),
    [query.data],
  );
  const brandUsers = useMemo(
    () => (query.data || []).filter((user) => hasOnlyAssignableRole(user, BRAND_USER_ROLE_CODE)),
    [query.data],
  );
  return {
    tenantId,
    ...query,
    tenantUsers,
    brandUsers,
  };
};

export const useTenantUserDetail = (userId: string) => {
  const { data: currentUser } = useGetMe();
  const tenantId = currentUser?.tenantId || "";
  const detailQuery = useGetTenantUser(tenantId, userId);
  const usersQuery = useGetTenantUsers(tenantId);
  const fallbackUser = useMemo(
    () =>
      (usersQuery.data || []).find((user) => {
        return user.id === userId || getTenantUserRequestId(user) === userId;
      }),
    [usersQuery.data, userId],
  );
  const user = detailQuery.data || fallbackUser;

  return {
    tenantId,
    ...detailQuery,
    data: user,
    isLoading: !user && (detailQuery.isLoading || usersQuery.isLoading),
    isFetching: detailQuery.isFetching || usersQuery.isFetching,
    isError: detailQuery.isError && !fallbackUser,
    error: fallbackUser ? null : detailQuery.error,
  };
};

export const useSaveTenantUser = (userId?: string) => {
  const { data: currentUser } = useGetMe();
  const tenantId = currentUser?.tenantId || "";
  const createMutation = useCreateTenantUser(tenantId);
  const updateMutation = useUpdateTenantUser(tenantId, userId || "");

  return userId
    ? {
        tenantId,
        ...updateMutation,
      }
    : {
        tenantId,
        ...createMutation,
      };
};
