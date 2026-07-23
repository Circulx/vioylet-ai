"use client";

import { useMutation } from "@tanstack/react-query";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";
import type {
  PipelineApproveRequest,
  PipelineEditImageTextRequest,
  PipelineEditImageTextResponse,
  PipelineRejectRequest,
  PipelineRunRequest,
  PipelineRunResponse,
} from "@/lib/api/contracts";

export function usePipeline() {
  const runPipeline = useMutation({
    mutationFn: (data: PipelineRunRequest) =>
      request<PipelineRunRequest, PipelineRunResponse>(API.PIPELINE.RUN, { data }),
  });

  const approveBlueprint = useMutation({
    mutationFn: (data: PipelineApproveRequest) =>
      request<PipelineApproveRequest, PipelineRunResponse>(API.PIPELINE.APPROVE, {
        data,
      }),
  });

  const rejectBlueprint = useMutation({
    mutationFn: (data: PipelineRejectRequest) =>
      request<PipelineRejectRequest, PipelineRunResponse>(API.PIPELINE.REJECT, { data }),
  });

  const editImageText = useMutation({
    mutationFn: (data: PipelineEditImageTextRequest) =>
      request<PipelineEditImageTextRequest, PipelineEditImageTextResponse>(
        API.PIPELINE.EDIT_IMAGE_TEXT,
        { data },
      ),
  });

  return {
    runPipeline,
    approveBlueprint,
    rejectBlueprint,
    editImageText,
    isLoading: runPipeline.isPending || approveBlueprint.isPending,
    isApproving: approveBlueprint.isPending,
    isEditingImage: editImageText.isPending,
    error: runPipeline.error || approveBlueprint.error || rejectBlueprint.error || editImageText.error,
    data: approveBlueprint.data ?? runPipeline.data,
  };
}
