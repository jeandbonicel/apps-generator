import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

interface PageHeaderProps {
  /** Page title */
  title: string;
  /** Optional description below the title */
  description?: string;
  /** Action buttons rendered on the right */
  children?: ReactNode;
  className?: string;
}

/**
 * Page header — consistent title + optional description + right-aligned actions.
 *
 * @example
 * <PageHeader title="Orders" description="47 total">
 *   <Button>Create Order</Button>
 * </PageHeader>
 */
export function PageHeader({
  title,
  description,
  children,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("flex items-start justify-between gap-4", className)}>
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {children && (
        <div className="flex items-center gap-[var(--spacing-tight)]">
          {children}
        </div>
      )}
    </div>
  );
}
