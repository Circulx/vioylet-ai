"use client";

import { useMutation } from "@tanstack/react-query";
import { API } from "@/lib/api/endpoints";
import { request } from "@/lib/api/request";
import type { PipelineRunRequest, PipelineRunResponse } from "@/lib/api/contracts";

export function usePipeline() {
  const runPipeline = useMutation({
    mutationFn: (data: PipelineRunRequest) =>
      request<PipelineRunRequest, PipelineRunResponse>(API.PIPELINE.RUN, { data }),
  });

  return {
    runPipeline,
    isLoading: runPipeline.isPending,
    error: runPipeline.error,
    data: runPipeline.data,
  };
}
