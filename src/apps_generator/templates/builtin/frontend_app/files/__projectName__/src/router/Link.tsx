{% raw %}
import type { ReactNode, MouseEvent } from "react";
import { navigateTo, getBasePath } from "./MfeRouter";

interface LinkProps {
  /** Sub-path to navigate to (e.g., "/123/edit") */
  to: string;
  children: ReactNode;
  className?: string;
}

/**
 * Navigation link for MFE internal routing.
 *
 * Usage:
 *   <Link to="/123">View Order</Link>
 *   <Link to="/123/edit" className="text-blue-600">Edit</Link>
 */
export function Link({ to, children, className }: LinkProps) {
  const handleClick = (e: MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    navigateTo(to);
  };

  const basePath = getBasePath();
  const href = to.startsWith("/") ? `${basePath}${to}` : `${basePath}/${to}`;

  return (
    <a href={href} onClick={handleClick} className={className}>
      {children}
    </a>
  );
}
{% endraw %}
