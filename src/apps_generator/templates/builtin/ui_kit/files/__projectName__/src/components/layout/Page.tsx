import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface PageProps {
  children: ReactNode;
  className?: string;
  /** Full width — no max-width constraint */
  fluid?: boolean;
}

/**
 * Page wrapper — enforces consistent max-width, padding, and vertical spacing.
 * Every MFE page should be wrapped in this component.
 *
 * @example
 * <Page>
 *   <PageHeader title="Orders" />
 *   <PageSection>
 *     <Table />
 *   </PageSection>
 * </Page>
 */
export function Page({ children, className, fluid = false }: PageProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-[var(--spacing-section)] p-[var(--spacing-page)]",
        !fluid && "mx-auto w-full max-w-[var(--page-max-width)]",
        className,
      )}
    >
      {children}
    </div>
  );
}
