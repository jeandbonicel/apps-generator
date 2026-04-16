{% if authProvider == "clerk" %}
import { useEffect } from "react";
import { useAuth } from "@clerk/clerk-react";
import { useTenant } from "../tenants/useTenant";

/**
 * Syncs shell auth/tenant React state to window globals so the shared
 * api-client (`useApiClient()`) works — both inside the shell and in
 * MFE remotes loaded via Module Federation.
 */
export function ShellContextSync() {
  const { getToken } = useAuth();
  const { currentTenant } = useTenant();

  useEffect(() => {
    (window as unknown as Record<string, unknown>).__SHELL_AUTH_TOKEN__ =
      () => getToken();
  }, [getToken]);

  useEffect(() => {
    (window as unknown as Record<string, unknown>).__SHELL_TENANT_ID__ =
      currentTenant?.id ?? null;
  }, [currentTenant]);

  return null;
}
{% else %}
import { useEffect } from "react";
import { useAuth } from "../auth/useAuth";
import { useTenant } from "../tenants/useTenant";

/**
 * Syncs shell auth/tenant React state to window globals so the shared
 * api-client (`useApiClient()`) works — both inside the shell and in
 * MFE remotes loaded via Module Federation.
 */
export function ShellContextSync() {
  const { getToken } = useAuth();
  const { currentTenant } = useTenant();

  useEffect(() => {
    (window as unknown as Record<string, unknown>).__SHELL_AUTH_TOKEN__ =
      () => getToken();
  }, [getToken]);

  useEffect(() => {
    (window as unknown as Record<string, unknown>).__SHELL_TENANT_ID__ =
      currentTenant?.id ?? null;
  }, [currentTenant]);

  return null;
}
{% endif %}
