export interface ApiConfig {
  /** Base URL for API calls (e.g., "/api" or "http://localhost:8080") */
  baseUrl: string;
  /** Async function to get the auth token */
  getToken: () => Promise<string | null>;
  /** Function to get the current tenant ID */
  getTenantId: () => string | null;
  /** Called when API returns 401 Unauthorized */
  onUnauthorized?: () => void;
  /** Called when API returns 403 Forbidden */
  onForbidden?: () => void;
}

export interface RequestOptions {
  headers?: Record<string, string>;
  params?: Record<string, string>;
  signal?: AbortSignal;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string,
    public readonly correlationId?: string,
  ) {
    super(`API Error ${status}: ${body}`);
    this.name = "ApiError";
  }

  get isUnauthorized() { return this.status === 401; }
  get isForbidden() { return this.status === 403; }
  get isNotFound() { return this.status === 404; }
  get isServerError() { return this.status >= 500; }
}
