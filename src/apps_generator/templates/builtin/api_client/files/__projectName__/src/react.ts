import { useMemo } from "react";
import { createApiClient, type ApiClient } from "./client";
import { getShellToken, getShellTenantId } from "./context";

/**
 * React hook that creates an API client pre-configured with
 * auth token and tenant ID from the platform shell context.
 *
 * @example
 * const api = useApiClient();
 * const orders = await api.get<Order[]>("/order");
 */
export function useApiClient(baseUrl = "/api"): ApiClient {
  return useMemo(
    () =>
      createApiClient({
        baseUrl,
        getToken: getShellToken,
        getTenantId: getShellTenantId,
        onUnauthorized: () => {
          window.dispatchEvent(new CustomEvent("api-unauthorized"));
        },
      }),
    [baseUrl],
  );
}
