"use client";

import { useQuery } from "@tanstack/react-query";

export type GoogleFontFamily = {
  family: string;
  category: string;
  variants: string[];
  version: string;
  lastModified: string;
};

type GoogleFontsResponse = {
  items: GoogleFontFamily[];
  error?: string;
};

export function useGoogleFonts() {
  return useQuery({
    queryKey: ["google-fonts"],
    staleTime: 1000 * 60 * 60 * 12,
    retry: false,
    queryFn: async () => {
      const response = await fetch("/api/google-fonts");
      const payload = (await response.json()) as GoogleFontsResponse;

      if (!response.ok) {
        throw new Error(payload.error || "Unable to load Google Fonts.");
      }

      return payload.items || [];
    },
  });
}
