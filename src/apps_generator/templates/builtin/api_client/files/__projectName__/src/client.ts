import { ApiConfig, ApiError, RequestOptions } from "./types";

function generateCorrelationId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older browsers
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function createApiClient(config: ApiConfig) {
  async function request<T = unknown>(
    method: string,
    path: string,
    body?: unknown,
    options?: RequestOptions,
  ): Promise<T> {
    const token = await config.getToken();
    const tenantId = config.getTenantId();
    const correlationId = generateCorrelationId();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "X-Correlation-ID": correlationId,
      ...options?.headers,
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (tenantId) {
      headers["X-Tenant-ID"] = tenantId;
    }

    let url = `${config.baseUrl}${path}`;
    if (options?.params) {
      const searchParams = new URLSearchParams(options.params);
      url += `?${searchParams.toString()}`;
    }

    const response = await fetch(url, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: options?.signal,
    });

    if (response.status === 401) {
      config.onUnauthorized?.();
      throw new ApiError(401, "Unauthorized", correlationId);
    }

    if (response.status === 403) {
      config.onForbidden?.();
      throw new ApiError(403, "Forbidden", correlationId);
    }

    if (!response.ok) {
      const text = await response.text().catch(() => "Unknown error");
      throw new ApiError(response.status, text, correlationId);
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  return {
    get: <T = unknown>(path: string, options?: RequestOptions) =>
      request<T>("GET", path, undefined, options),

    post: <T = unknown>(path: string, body?: unknown, options?: RequestOptions) =>
      request<T>("POST", path, body, options),

    put: <T = unknown>(path: string, body?: unknown, options?: RequestOptions) =>
      request<T>("PUT", path, body, options),

    patch: <T = unknown>(path: string, body?: unknown, options?: RequestOptions) =>
      request<T>("PATCH", path, body, options),

    delete: <T = unknown>(path: string, options?: RequestOptions) =>
      request<T>("DELETE", path, undefined, options),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
