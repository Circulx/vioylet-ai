import { useMutation, useQueryClient } from "@tanstack/react-query";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";
import type { TenantUserResponse } from "@/lib/api/contracts";

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
