import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface PageGridProps {
  /** Number of columns at large breakpoint (default: 3) */
  columns?: 1 | 2 | 3 | 4;
  children: ReactNode;
  className?: string;
}

const colClasses = {
  1: "grid-cols-1",
  2: "grid-cols-1 md:grid-cols-2",
  3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
  4: "grid-cols-1 md:grid-cols-2 lg:grid-cols-4",
};

/**
 * Responsive grid with consistent gap. Always starts as 1 column on mobile.
 *
 * @example
 * <PageGrid columns={3}>
 *   <Card>...</Card>
 *   <Card>...</Card>
 *   <Card>...</Card>
 * </PageGrid>
 */
export function PageGrid({ columns = 3, children, className }: PageGridProps) {
  return (
    <div
      className={cn(
        "grid gap-[var(--spacing-inline)]",
        colClasses[columns],
        className,
      )}
    >
      {children}
    </div>
  );
}
