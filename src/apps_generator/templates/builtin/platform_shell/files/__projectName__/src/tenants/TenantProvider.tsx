{% if authProvider == "clerk" %}
import {
  createContext,
  type ReactNode,
} from "react";
import { useOrganization } from "@clerk/clerk-react";
import type { Tenant } from "../types";

export interface TenantContextValue {
  tenants: Tenant[];
  currentTenant: Tenant | null;
  switchTenant: (tenantId: string) => void;
  isLoading: boolean;
  error: string | null;
}

export const TenantContext = createContext<TenantContextValue>({
  tenants: [],
  currentTenant: null,
  switchTenant: () => {},
  isLoading: false,
  error: null,
});

interface TenantProviderProps {
  children: ReactNode;
}

export function TenantProvider({ children }: TenantProviderProps) {
  const { organization, isLoaded } = useOrganization();

  const currentTenant: Tenant | null = organization
    ? { id: organization.id, name: organization.name }
    : null;

  const contextValue: TenantContextValue = {
    tenants: currentTenant ? [currentTenant] : [],
    currentTenant,
    switchTenant: () => {},
    isLoading: !isLoaded,
    error: null,
  };

  return (
    <TenantContext.Provider value={contextValue}>
      {children}
    </TenantContext.Provider>
  );
}
{% else %}
import {
  createContext,
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useAuth } from "react-oidc-context";
import type { Tenant } from "../types";

export interface TenantContextValue {
  tenants: Tenant[];
  currentTenant: Tenant | null;
  switchTenant: (tenantId: string) => void;
  isLoading: boolean;
  error: string | null;
}

export const TenantContext = createContext<TenantContextValue>({
  tenants: [],
  currentTenant: null,
  switchTenant: () => {},
  isLoading: false,
  error: null,
});

const STORAGE_KEY = "{{ projectName }}_current_tenant";

interface TenantProviderProps {
  children: ReactNode;
}

export function TenantProvider({ children }: TenantProviderProps) {
  const auth = useAuth();
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!auth.isAuthenticated || !auth.user?.access_token) return;

    setIsLoading(true);
    setError(null);

    fetch("{{ tenantsEndpoint }}", {
      headers: {
        Authorization: `Bearer ${auth.user.access_token}`,
      },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to fetch tenants: ${res.status}`);
        return res.json();
      })
      .then((data: Tenant[]) => {
        setTenants(data);

        const savedId = localStorage.getItem(STORAGE_KEY);
        const saved = data.find((t) => t.id === savedId);
        setCurrentTenant(saved ?? data[0] ?? null);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load tenants");
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, [auth.isAuthenticated, auth.user?.access_token]);

  const switchTenant = useCallback(
    (tenantId: string) => {
      const tenant = tenants.find((t) => t.id === tenantId);
      if (tenant) {
        setCurrentTenant(tenant);
        localStorage.setItem(STORAGE_KEY, tenantId);
      }
    },
    [tenants],
  );

  const contextValue: TenantContextValue = {
    tenants,
    currentTenant,
    switchTenant,
    isLoading,
    error,
  };

  return (
    <TenantContext.Provider value={contextValue}>
      {children}
    </TenantContext.Provider>
  );
}
{% endif %}
