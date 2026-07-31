import { useMutation, useQueryClient } from "@tanstack/react-query";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";
import type { TenantSummaryResponse, TenantUserResponse } from "@/lib/api/contracts";
import { toast } from "@/components/ui/use-toast";
import { refreshNotificationQueries } from "@/lib/notification-queries";

function compactTenantUsers(users?: TenantUserResponse[]) {
  if (!users) {
    return users;
  }
  const seen = new Set<string>();
  return users.filter((user) => {
    const stableId = user.user_id || user.id;
    if (seen.has(stableId)) {
      return false;
    }
    seen.add(stableId);
    return true;
  });
}

function tenantUserMatches(user: TenantUserResponse, ids: Set<string>) {
  return ids.has(user.id) || (user.user_id ? ids.has(user.user_id) : false);
}

function updateTenantAdminAccountStatus(
  tenant: TenantSummaryResponse | undefined,
  userId: string,
  isActive: boolean,
) {
  if (!tenant || tenant.tenant_admin_user_id !== userId) {
    return tenant;
  }
  return {
    ...tenant,
    tenant_admin_is_active: isActive,
  };
}

export const useUpdateTenantAdmin = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: unknown }) =>
      request(API.TENANTS.UPDATE, {
        pathParams: id,
        data,
      }),
    onSuccess: async (_, variables) => {
      await queryClient.invalidateQueries({ queryKey: ["tenants"] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", variables.id] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", variables.id, "usage-summary"] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", variables.id, "users"] });
    },
  });
};

export const useUpdateBrandUsageTargets = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, brandUsageTargets }: { id: string; brandUsageTargets: Record<string, number> }) =>
      request(API.TENANTS.UPDATE_BRAND_USAGE_TARGETS, {
        pathParams: id,
        data: { brand_usage_targets: brandUsageTargets },
      }),
    onSuccess: (response, variables) => {
      queryClient.setQueryData(["tenant", variables.id], (current: unknown) => {
        if (!current || typeof current !== "object") {
          return current;
        }
        const tenant = current as { metadata_json?: Record<string, unknown> };
        return {
          ...tenant,
          metadata_json: {
            ...(tenant.metadata_json || {}),
            brand_usage_targets: response.brand_usage_targets,
          },
        };
      });
      void queryClient.invalidateQueries({ queryKey: ["tenant", variables.id], refetchType: "inactive" });
      void queryClient.invalidateQueries({ queryKey: ["tenant", variables.id, "usage-summary"] });
      void refreshNotificationQueries(queryClient);
    },
  });
};

export const useDeleteTenantAdmin = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      request(API.TENANTS.DELETE, {
        pathParams: id,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tenants"] });
      toast({
        title: "Tenant deleted successfully.",
        variant: "success",
      });
    },
  });
};

export const useUploadTenantLogo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: unknown }) =>
      request(API.TENANTS.UPLOAD_LOGO, {
        pathParams: id,
        data,
      }),
    onSuccess: async (_, variables) => {
      await queryClient.invalidateQueries({ queryKey: ["tenants"] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", variables.id] });
    },
  });
};

export const useRemoveTenantLogo = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) =>
      request(API.TENANTS.REMOVE_LOGO, {
        pathParams: id,
      }),
    onSuccess: async (_, id) => {
      await queryClient.invalidateQueries({ queryKey: ["tenants"] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", id] });
    },
  });
};

export const useUpdateTenantUser = (tenantId: string, userId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: unknown) =>
      request(API.TENANTS.UPDATE_USER, {
        pathParams: { tenantId, userId },
        data,
      }),
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(["tenant", tenantId, "user", userId], updatedUser);
      queryClient.setQueryData<TenantUserResponse[]>(["tenant", tenantId, "users"], (current) =>
        current?.map((user) => (user.id === updatedUser.id ? updatedUser : user)),
      );
      void queryClient.invalidateQueries({ queryKey: ["tenant", tenantId, "users"] });
      void queryClient.invalidateQueries({ queryKey: ["tenant", tenantId, "user", userId] });
      void refreshNotificationQueries(queryClient);
    },
  });
};

export const useDeactivateTenantUser = (tenantId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) =>
      request(API.TENANTS.DEACTIVATE_USER, {
        pathParams: { tenantId, userId },
      }),
    onSuccess: async (_response, userId) => {
      queryClient.setQueriesData<TenantUserResponse[]>({ queryKey: ["tenant", tenantId, "users"] }, (current) =>
        compactTenantUsers(
          current?.map((user) =>
            tenantUserMatches(user, new Set([userId]))
              ? { ...user, is_active: false }
              : user,
          ),
        ),
      );
      queryClient.setQueryData<TenantSummaryResponse>(["tenant", tenantId], (current) =>
        updateTenantAdminAccountStatus(current, userId, false),
      );
      queryClient.setQueryData<TenantSummaryResponse[]>(["tenants"], (current) =>
        current?.map((tenant) => updateTenantAdminAccountStatus(tenant, userId, false) || tenant),
      );
      await queryClient.invalidateQueries({ queryKey: ["tenant", tenantId, "users"] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", tenantId, "user", userId] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", tenantId] });
      await queryClient.invalidateQueries({ queryKey: ["tenants"] });
      await refreshNotificationQueries(queryClient);
    },
  });
};

export const useReactivateTenantUser = (tenantId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) =>
      request(API.TENANTS.UPDATE_USER, {
        pathParams: { tenantId, userId },
        data: { is_active: true },
      }),
    onSuccess: async (updatedUser, userId) => {
      const targetIds = new Set([userId, updatedUser.id, updatedUser.user_id].filter((id): id is string => Boolean(id)));
      queryClient.setQueryData(["tenant", tenantId, "user", userId], updatedUser);
      queryClient.setQueriesData<TenantUserResponse[]>({ queryKey: ["tenant", tenantId, "users"] }, (current) =>
        compactTenantUsers(
          current?.map((user) =>
            tenantUserMatches(user, targetIds)
              ? updatedUser
              : user,
          ),
        ),
      );
      queryClient.setQueryData<TenantSummaryResponse>(["tenant", tenantId], (current) =>
        updateTenantAdminAccountStatus(current, userId, updatedUser.is_active),
      );
      queryClient.setQueryData<TenantSummaryResponse[]>(["tenants"], (current) =>
        current?.map((tenant) => updateTenantAdminAccountStatus(tenant, userId, updatedUser.is_active) || tenant),
      );
      await queryClient.invalidateQueries({ queryKey: ["tenant", tenantId, "users"] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", tenantId, "user", userId] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", tenantId] });
      await queryClient.invalidateQueries({ queryKey: ["tenants"] });
      await refreshNotificationQueries(queryClient);
    },
  });
};

export const useResendTenantUserActivation = (tenantId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: string | { tenantId: string; userId: string }) => {
      const resolvedTenantId = typeof params === "string" ? tenantId : params.tenantId;
      const userId = typeof params === "string" ? params : params.userId;
      return request(API.TENANTS.RESEND_ACTIVATION, {
        pathParams: { tenantId: resolvedTenantId, userId },
      });
    },
    onSuccess: async (_delivery, params) => {
      const resolvedTenantId = typeof params === "string" ? tenantId : params.tenantId;
      await queryClient.invalidateQueries({ queryKey: ["tenant", resolvedTenantId, "users"] });
      await queryClient.invalidateQueries({ queryKey: ["tenants"] });
      await queryClient.invalidateQueries({ queryKey: ["tenant", resolvedTenantId] });
    },
  });
};
