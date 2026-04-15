import { useCallback } from "react";
import { useAuth } from "../auth/useAuth";
import { useTenant } from "../tenants/useTenant";

interface FetchOptions extends Omit<RequestInit, "headers"> {
  headers?: Record<string, string>;
}

export function useApi() {
  const { getToken } = useAuth();
  const { currentTenant } = useTenant();

  const apiFetch = useCallback(
    async <T = unknown>(path: string, options: FetchOptions = {}): Promise<T> => {
      const url = path.startsWith("http") ? path : `{{ apiBaseUrl }}${path}`;

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...options.headers,
      };

      const token = await getToken();
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      if (currentTenant) {
        headers["X-Tenant-ID"] = currentTenant.id;
      }

      const response = await fetch(url, { ...options, headers });

      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }

      return response.json();
    },
    [getToken, currentTenant],
  );

  return { apiFetch };
}
