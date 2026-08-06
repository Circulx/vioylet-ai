import { InfiniteData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";
import type { ChatEnhancePromptRequest, ChatMessageResponse, ChatPipelineRecordRequest, ChatSessionResponse, ChatSessionUpdateRequest, ImageEditApplyRequest, ImageEditStateRequest, ReviewShareAccessUpdateRequest, StudioPanelSelection } from "@/lib/api/contracts";

const CHAT_MESSAGES_PAGE_SIZE = 10;

type ChatMessageCursor = {
  created_at: string;
  id: string;
};

function brandHeaders(brandId: string) {
  return {
    "X-Brand-Space-Id": brandId,
  };
}

export const useContentHistory = (brandId: string) =>
  useQuery({
    queryKey: ["brand", brandId, "content-history"],
    enabled: Boolean(brandId),
    queryFn: () =>
      request(API.CONTENT.HISTORY, {
        headers: brandHeaders(brandId),
      }),
  });

export const useGenerateContent = (brandId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: unknown) =>
      request(API.CONTENT.GENERATE, {
        data,
        headers: brandHeaders(brandId),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["brand", brandId, "content-history"] });
    },
  });
};

export const useExportContent = (brandId: string) =>
  useMutation({
    mutationFn: (data: unknown) =>
      request(API.CONTENT.EXPORT, {
        data,
        headers: brandHeaders(brandId),
      }),
  });

export const useEnhancePrompt = (brandId: string) =>
  useMutation({
    mutationFn: (data: ChatEnhancePromptRequest) =>
      request(API.CHAT.ENHANCE_PROMPT, {
        data,
        headers: brandHeaders(brandId),
      }),
  });


export const useImageEditState = (brandId: string) =>
  useMutation({
    mutationFn: (data: ImageEditStateRequest) =>
      request(API.CONTENT.IMAGE_EDIT_STATE, {
        data,
        headers: brandHeaders(brandId),
      }),
  });

export const useApplyImageEdit = (brandId: string) =>
  useMutation({
    mutationFn: (data: ImageEditApplyRequest) =>
      request(API.CONTENT.IMAGE_EDIT_APPLY, {
        data,
        headers: brandHeaders(brandId),
      }),
  });
export const useTemplateRecommendations = (
  brandId: string,
  prompt: string,
  studioPanel: StudioPanelSelection,
  limit = 3,
  enabled = true,
) =>
  useQuery({
    queryKey: ["brand", brandId, "template-recommendations", prompt, studioPanel, limit],
    enabled: enabled && Boolean(brandId) && Boolean(prompt.trim()),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    queryFn: () =>
      request(API.TEMPLATES.RECOMMEND, {
        data: {
          prompt,
          studio_panel: studioPanel,
          limit,
        },
        headers: brandHeaders(brandId),
      }),
  });

export const useToneCheck = (brandId: string) =>
  useMutation({
    mutationFn: (data: unknown) =>
      request(API.CONTENT.TONE_CHECK, {
        data,
        headers: brandHeaders(brandId),
      }),
  });

export const useCreateChatSession = (brandId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: unknown) =>
      request(API.CHAT.CREATE_SESSION, {
        data,
        headers: brandHeaders(brandId),
      }),
    onSuccess: async (session) => {
      queryClient.setQueryData(["brand", brandId, "chat-sessions"], (current: Array<{ id: string }> | undefined) => {
        if (!current) {
          return [session];
        }
        const next = current.filter((item) => item.id !== session.id);
        return [session, ...next];
      });
      await queryClient.invalidateQueries({ queryKey: ["brand", brandId, "chat-sessions"] });
    },
  });
};

export const useChatSessions = (brandId: string) =>
  useQuery({
    queryKey: ["brand", brandId, "chat-sessions"],
    enabled: Boolean(brandId),
    staleTime: 15_000,
    refetchOnWindowFocus: true,
    queryFn: () =>
      request(API.CHAT.LIST_SESSIONS, {
        headers: brandHeaders(brandId),
      }),
  });

export const useUpdateChatSession = (brandId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: string; data: ChatSessionUpdateRequest }) =>
      request(API.CHAT.UPDATE_SESSION, {
        pathParams: sessionId,
        data,
        headers: brandHeaders(brandId),
      }),
    onMutate: async ({ sessionId, data }) => {
      const queryKey = ["brand", brandId, "chat-sessions"];
      await queryClient.cancelQueries({ queryKey });
      const previousSessions = queryClient.getQueryData<ChatSessionResponse[]>(queryKey);
      if (data.title !== undefined) {
        queryClient.setQueryData<ChatSessionResponse[]>(queryKey, (current) =>
          (current || []).map((item) => (item.id === sessionId ? { ...item, title: data.title } : item)),
        );
      }
      return { previousSessions };
    },
    onError: (_error, _variables, context) => {
      if (context?.previousSessions) {
        queryClient.setQueryData(["brand", brandId, "chat-sessions"], context.previousSessions);
      }
    },
    onSuccess: (session) => {
      queryClient.setQueryData<ChatSessionResponse[]>(["brand", brandId, "chat-sessions"], (current) => {
        if (!current) {
          return [session];
        }
        return current.map((item) => (item.id === session.id ? session : item));
      });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["brand", brandId, "chat-sessions"] });
    },
  });
};

export const useDeleteChatSession = (brandId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) =>
      request(API.CHAT.DELETE_SESSION, {
        pathParams: sessionId,
        headers: brandHeaders(brandId),
      }),
    onMutate: async (sessionId) => {
      const queryKey = ["brand", brandId, "chat-sessions"];
      await queryClient.cancelQueries({ queryKey });
      const previousSessions = queryClient.getQueryData<ChatSessionResponse[]>(queryKey);
      queryClient.setQueryData<ChatSessionResponse[]>(queryKey, (current) =>
        (current || []).filter((item) => item.id !== sessionId),
      );
      queryClient.removeQueries({ queryKey: ["brand", brandId, "chat-session", sessionId, "messages"] });
      return { previousSessions };
    },
    onError: (_error, _sessionId, context) => {
      if (context?.previousSessions) {
        queryClient.setQueryData(["brand", brandId, "chat-sessions"], context.previousSessions);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ["brand", brandId, "chat-sessions"] });
    },
  });
};

export const useChatMessages = (brandId: string, sessionId: string) =>
  useInfiniteQuery({
    queryKey: ["brand", brandId, "chat-session", sessionId, "messages"],
    enabled: Boolean(brandId && sessionId),
    staleTime: 0,
    retry: 1,
    initialPageParam: undefined as ChatMessageCursor | undefined,
    queryFn: ({ pageParam }) =>
      request(API.CHAT.LIST_MESSAGES, {
        pathParams: sessionId,
        params: {
          limit: CHAT_MESSAGES_PAGE_SIZE,
          before_created_at: pageParam?.created_at,
          before_id: pageParam?.id,
        },
        headers: brandHeaders(brandId),
      }),
    getNextPageParam: (lastPage: ChatMessageResponse[]) => {
      if (lastPage.length < CHAT_MESSAGES_PAGE_SIZE) {
        return undefined;
      }
      const oldestMessage = lastPage[0];
      return oldestMessage ? { created_at: oldestMessage.created_at, id: oldestMessage.id } : undefined;
    },
    select: (data) => [...data.pages].reverse().flat(),
  });

export const useSendChatMessage = (brandId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, data, signal }: { sessionId: string; data: unknown; signal?: AbortSignal }) =>
      request(API.CHAT.SEND_MESSAGE, {
        pathParams: sessionId,
        data,
        headers: brandHeaders(brandId),
        signal,
      }),
    onSuccess: async (response, variables) => {
      queryClient.setQueryData<InfiniteData<ChatMessageResponse[]>>(
        ["brand", brandId, "chat-session", variables.sessionId, "messages"],
        (current) => {
          if (!current) {
            return {
              pages: [[response.user_message, response.assistant_message]],
              pageParams: [undefined],
            };
          }
          const seen = new Set(current.pages.flat().map((item) => item.id));
          const appended = [response.user_message, response.assistant_message].filter((item) => !seen.has(item.id));
          if (!appended.length) {
            return current;
          }
          const pages = current.pages.length ? [...current.pages] : [[]];
          pages[0] = [...(pages[0] || []), ...appended];
          return {
            ...current,
            pages,
          };
        },
      );
      await queryClient.invalidateQueries({
        queryKey: ["brand", brandId, "chat-session", variables.sessionId, "messages"],
      });
      await queryClient.invalidateQueries({ queryKey: ["brand", brandId, "content-history"] });
      await queryClient.invalidateQueries({ queryKey: ["brand", brandId, "chat-sessions"] });
    },
  });
};

export const useCancelChatGeneration = (brandId: string) =>
  useMutation({
    mutationFn: (sessionId: string) =>
      request(API.CHAT.CANCEL_GENERATION, {
        pathParams: sessionId,
        headers: brandHeaders(brandId),
      }),
  });

export const useRecordPipelineResult = (brandId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, data }: { sessionId: string; data: ChatPipelineRecordRequest }) =>
      request(API.CHAT.RECORD_PIPELINE_RESULT, {
        pathParams: sessionId,
        data,
        headers: brandHeaders(brandId),
      }),
    onSuccess: async (response, variables) => {
      queryClient.setQueryData<InfiniteData<ChatMessageResponse[]>>(
        ["brand", brandId, "chat-session", variables.sessionId, "messages"],
        (current) => {
          if (!current) {
            return {
              pages: [[response.user_message, response.assistant_message]],
              pageParams: [undefined],
            };
          }
          const seen = new Set(current.pages.flat().map((item) => item.id));
          const appended = [response.user_message, response.assistant_message].filter((item) => !seen.has(item.id));
          if (!appended.length) {
            return current;
          }
          const pages = current.pages.length ? [...current.pages] : [[]];
          pages[0] = [...(pages[0] || []), ...appended];
          return {
            ...current,
            pages,
          };
        },
      );
      await queryClient.invalidateQueries({
        queryKey: ["brand", brandId, "chat-session", variables.sessionId, "messages"],
      });
      await queryClient.invalidateQueries({ queryKey: ["brand", brandId, "chat-sessions"] });
    },
  });
};

export const useCreateShareLink = (brandId: string) =>
  useMutation({
    mutationFn: (data: unknown) =>
      request(API.REVIEW.CREATE_LINK, {
        data,
        headers: brandHeaders(brandId),
      }),
  });

export const useReviewDetail = (token: string) =>
  useQuery({
    queryKey: ["review", token],
    enabled: Boolean(token),
    queryFn: () => request(API.REVIEW.DETAIL, { pathParams: token }),
  });

export const useReviewShareAccess = (token: string, enabled = true) =>
  useQuery({
    queryKey: ["review", token, "share-access"],
    enabled: Boolean(token) && enabled,
    queryFn: () => request(API.REVIEW.SHARE_ACCESS, { pathParams: token }),
  });

export const useUpdateReviewShareAccess = (token: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ReviewShareAccessUpdateRequest) =>
      request(API.REVIEW.UPDATE_SHARE_ACCESS, {
        pathParams: token,
        data,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["review", token, "share-access"] });
      await queryClient.invalidateQueries({ queryKey: ["review", token] });
    },
  });
};

export const useAddReviewComment = (token: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: unknown) =>
      request(API.REVIEW.ADD_COMMENT, {
        pathParams: token,
        data,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["review", token] });
    },
  });
};

export const useUpdateReviewStatus = (token: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { status: string }) =>
      request(API.REVIEW.UPDATE_STATUS, {
        pathParams: token,
        data,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["review", token] });
    },
  });
};

export const useTenantAnalytics = (enabled = true) =>
  useQuery({
    queryKey: ["analytics", "tenant"],
    enabled,
    queryFn: () => request(API.ANALYTICS.TENANT),
  });

export const usePlatformAnalytics = (enabled = true) =>
  useQuery({
    queryKey: ["analytics", "platform"],
    enabled,
    queryFn: () => request(API.ANALYTICS.PLATFORM),
  });

export const useKnowledgeAssets = (brandId: string) =>
  useQuery({
    queryKey: ["brand", brandId, "knowledge-assets"],
    enabled: Boolean(brandId),
    queryFn: () =>
      request(API.KNOWLEDGE.LIST, {
        headers: brandHeaders(brandId),
      }),
  });

export const useUploadKnowledgeAsset = (brandId: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: unknown) =>
      request(API.KNOWLEDGE.UPLOAD, {
        data,
        headers: brandHeaders(brandId),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["brand", brandId, "knowledge-assets"] });
    },
  });
};
