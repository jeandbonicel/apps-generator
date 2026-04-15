{% raw %}
import { useState, useEffect, type ReactNode } from "react";
import { getSubPath, matchPattern } from "./MfeRouter";

interface SubRouteProps {
  /** Route pattern, e.g. "/", "/:id", "/:id/edit" */
  path: string;
  children: ReactNode | ((params: Record<string, string>) => ReactNode);
}

/**
 * Renders children only when the current sub-path matches the pattern.
 *
 * Usage:
 *   <SubRoute path="/">          <OrderList /></SubRoute>
 *   <SubRoute path="/:id">      {(params) => <OrderDetail id={params.id} />}</SubRoute>
 *   <SubRoute path="/:id/edit"> <OrderEdit /></SubRoute>
 */
export function SubRoute({ path, children }: SubRouteProps) {
  const [subPath, setSubPath] = useState(getSubPath);

  useEffect(() => {
    const update = () => setSubPath(getSubPath());
    window.addEventListener("popstate", update);
    window.addEventListener("mfe-navigate", update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener("mfe-navigate", update);
    };
  }, []);

  const match = matchPattern(path, subPath);
  if (!match) return null;

  if (typeof children === "function") {
    return <>{children(match.params)}</>;
  }

  return <>{children}</>;
}
{% endraw %}
