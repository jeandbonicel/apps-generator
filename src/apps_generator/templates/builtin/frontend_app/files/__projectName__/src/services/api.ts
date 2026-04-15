import { apiFetch } from "../hooks/useApi";

/**
 * Example API client.
 *
 * Add domain-specific API calls here. Each function uses the shared
 * `apiFetch` helper which automatically handles auth tokens and
 * tenant context from the platform shell.
 */

export interface HealthResponse {
  status: string;
  version?: string;
}

export const api = {
  /** Health-check endpoint */
  getHealth(): Promise<HealthResponse> {
    return apiFetch<HealthResponse>("/health");
  },

  // Add more API methods here, e.g.:
  // getItems(): Promise<Item[]> {
  //   return apiFetch<Item[]>("/items");
  // },
};
