/**
 * Get the auth token from the platform shell context.
 * The shell sets window.__SHELL_AUTH_TOKEN__ after login.
 * Supports both sync (string) and async (function) values.
 */
export async function getShellToken(): Promise<string | null> {
  const tokenOrFn = (window as unknown as Record<string, unknown>).__SHELL_AUTH_TOKEN__;
  if (typeof tokenOrFn === "function") {
    return tokenOrFn() as Promise<string | null>;
  }
  return (tokenOrFn as string) || null;
}

/**
 * Get the current tenant ID from the platform shell context.
 * The shell sets window.__SHELL_TENANT_ID__ when the user selects an organization.
 */
export function getShellTenantId(): string | null {
  return ((window as unknown as Record<string, unknown>).__SHELL_TENANT_ID__ as string) || null;
}
