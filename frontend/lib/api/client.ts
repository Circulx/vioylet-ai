import axios from "axios";
import { clearAuthTokens, getAccessToken } from "@/lib/api/session";
import { apiOrigin } from "@/lib/env";

export const apiClient = axios.create({
  baseURL: apiOrigin,
  withCredentials: false,
});

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error?.response?.status === 401) {
      clearAuthTokens();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/auth/")) {
        window.location.href = "/auth/login";
      }
    }
    return Promise.reject(error);
  },
);
