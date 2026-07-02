import { useMemo } from "react";
import { useCreateTenantUser } from "@/hooks/tenantAdmins/useCreateTenant";
import { useGetTenantUser, useGetTenantUsers } from "@/hooks/tenantAdmins/useGetTenants";
import { useUpdateTenantUser } from "@/hooks/tenantAdmins/useUpdateTenant";
import { useGetMe } from "@/hooks/useUser";
import type { TenantUserResponse } from "@/lib/api/contracts";

export function getTenantUserRequestId(user?: TenantUserResponse | null) {
  return user?.user_id || user?.id || "";
}

export const useTenantUsers = () => {
  const { data: currentUser } = useGetMe();
  const tenantId = currentUser?.tenantId || "";
  const query = useGetTenantUsers(tenantId);
  const tenantUsers = useMemo(
    () => (query.data || []).filter((user) => !user.role_codes.includes("brand_user")),
    [query.data],
  );
  const brandUsers = useMemo(
    () => (query.data || []).filter((user) => user.role_codes.includes("brand_user")),
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
