/**
 * Shared type definitions for {{ projectTitle or projectName }}.
 */

/** Shell context injected by the platform host */
export interface ShellContext {
  tenantId?: string;
  accessToken?: string;
  basePath?: string;
}

/** Extend the global Window type so TypeScript knows about __SHELL_CONTEXT__ */
declare global {
  interface Window {
    __SHELL_CONTEXT__?: ShellContext;
  }
}
