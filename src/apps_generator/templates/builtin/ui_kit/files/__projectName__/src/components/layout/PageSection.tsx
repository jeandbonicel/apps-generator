import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface PageSectionProps {
  /** Optional section title */
  title?: string;
  /** Optional description */
  description?: string;
  children: ReactNode;
  className?: string;
}

/**
 * A vertical section within a page. Use between `<Page>` children
 * for consistent spacing. Optional title renders as h2.
 *
 * @example
 * <Page>
 *   <PageSection title="Recent Orders">
 *     <Table />
 *   </PageSection>
 * </Page>
 */
export function PageSection({
  title,
  description,
  children,
  className,
}: PageSectionProps) {
  return (
    <section className={cn("flex flex-col gap-[var(--spacing-inline)]", className)}>
      {(title || description) && (
        <div>
          {title && (
            <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
          )}
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      )}
      {children}
    </section>
  );
}
