const API_BASE = "{{ apiBaseUrl }}";

/**
 * Context that the platform shell may inject when loading this remote.
 * In standalone mode these values fall back to defaults.
 */
interface ShellContext {
  tenantId?: string;
  accessToken?: string;
}

function getShellContext(): ShellContext {
  // When loaded as a Module Federation remote, the shell may place
  // context on window.__SHELL_CONTEXT__.  In standalone dev mode this
  // will be undefined and we use sensible defaults.
  const ctx = (window as Record<string, unknown>).__SHELL_CONTEXT__ as
    | ShellContext
    | undefined;
  return ctx ?? {};
}

interface FetchOptions extends Omit<RequestInit, "headers"> {
  headers?: Record<string, string>;
}

/**
 * Thin fetch wrapper that:
 * - Prepends the API base URL
 * - Attaches the bearer token from the shell context (if available)
 * - Sets the tenant header (if available)
 */
export async function apiFetch<T = unknown>(
  path: string,
  options: FetchOptions = {},
): Promise<T> {
  const { accessToken, tenantId } = getShellContext();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  if (tenantId) {
    headers["X-Tenant-Id"] = tenantId;
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

/**
 * React hook for convenient API access.
 */
export function useApi() {
  return { apiFetch };
}
