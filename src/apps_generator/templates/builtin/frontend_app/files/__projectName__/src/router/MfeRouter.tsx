/**
 * Lightweight MFE router — plain functions, no React hooks.
 *
 * Works reliably across the Module Federation boundary because
 * it reads from window.location directly instead of React context.
 */

/** Get the base path this MFE is mounted at */
export function getBasePath(): string {
  return ((window as unknown as Record<string, unknown>).__MFE_BASE_PATH__ as string) || "/";
}

/** Get the current sub-path relative to the base path */
export function getSubPath(): string {
  const basePath = getBasePath();
  const pathname = window.location.pathname;
  const sub = pathname.slice(basePath.length);
  return sub.startsWith("/") ? sub : `/${sub}`;
}

/** Navigate to a sub-path within this MFE */
export function navigateTo(subPath: string): void {
  const basePath = getBasePath();
  const fullPath = subPath.startsWith("/")
    ? `${basePath}${subPath}`
    : `${basePath}/${subPath}`;

  window.history.pushState({}, "", fullPath);
  // Dispatch event so React components can react to navigation
  window.dispatchEvent(new Event("mfe-navigate"));
}

/** Match a route pattern against a path, extracting params */
export function matchPattern(
  pattern: string,
  path: string,
): { params: Record<string, string> } | null {
  const normPattern = pattern === "/" ? "/" : pattern.replace(/\/+$/, "");
  const normPath = path === "/" ? "/" : path.replace(/\/+$/, "");

  const patternParts = normPattern.split("/").filter(Boolean);
  const pathParts = normPath.split("/").filter(Boolean);

  if (patternParts.length === 0 && pathParts.length === 0) {
    return { params: {} };
  }

  if (patternParts.length !== pathParts.length) {
    return null;
  }

  const params: Record<string, string> = {};

  for (let i = 0; i < patternParts.length; i++) {
    const pp = patternParts[i];
    const pathPart = pathParts[i];

    if (pp.startsWith(":")) {
      params[pp.slice(1)] = decodeURIComponent(pathPart);
    } else if (pp !== pathPart) {
      return null;
    }
  }

  return { params };
}
