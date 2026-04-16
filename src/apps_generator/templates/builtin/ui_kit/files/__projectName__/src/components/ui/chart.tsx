{% raw %}
import * as React from "react";
import { ResponsiveContainer, Tooltip, Legend } from "recharts";
import { cn } from "@/lib/utils";

// ── Chart config type ───────────────────────────────────────────────────────

export type ChartConfig = Record<
  string,
  {
    label: string;
    color?: string; // CSS variable like "hsl(var(--chart-1))"
    icon?: React.ComponentType;
  }
>;

// ── Chart container ─────────────────────────────────────────────────────────

interface ChartContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  config: ChartConfig;
  children: React.ReactElement;
}

const ChartContainer = React.forwardRef<HTMLDivElement, ChartContainerProps>(
  ({ config, className, children, ...props }, ref) => {
    // Inject chart colors as CSS variables
    const style: React.CSSProperties = {};
    Object.entries(config).forEach(([key, value], index) => {
      if (value.color) {
        style[`--color-${key}` as string] = value.color;
      } else {
        style[`--color-${key}` as string] = `hsl(var(--chart-${index + 1}))`;
      }
    });

    return (
      <div
        ref={ref}
        className={cn("flex aspect-video justify-center text-xs", className)}
        style={style}
        {...props}
      >
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    );
  }
);
ChartContainer.displayName = "ChartContainer";

// ── Chart tooltip ───────────────────────────────────────────────────────────

interface ChartTooltipContentProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    color: string;
    dataKey: string;
    payload: Record<string, unknown>;
  }>;
  label?: string;
  config?: ChartConfig;
  hideLabel?: boolean;
  indicator?: "dot" | "line" | "dashed";
}

function ChartTooltipContent({
  active,
  payload,
  label,
  config,
  hideLabel = false,
  indicator = "dot",
}: ChartTooltipContentProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border bg-background p-2 shadow-sm">
      {!hideLabel && label && (
        <p className="mb-1.5 text-xs font-medium text-muted-foreground">{label}</p>
      )}
      <div className="flex flex-col gap-1">
        {payload.map((entry, index) => {
          const key = entry.dataKey ?? entry.name;
          const configEntry = config?.[key];
          const displayLabel = configEntry?.label ?? entry.name;
          const color = entry.color || `var(--color-${key})`;

          return (
            <div key={index} className="flex items-center gap-2 text-xs">
              {indicator === "dot" && (
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{ backgroundColor: color }}
                />
              )}
              {indicator === "line" && (
                <span
                  className="h-0.5 w-3 shrink-0 rounded-full"
                  style={{ backgroundColor: color }}
                />
              )}
              {indicator === "dashed" && (
                <span
                  className="h-0.5 w-3 shrink-0 rounded-full border-b-2 border-dashed"
                  style={{ borderColor: color }}
                />
              )}
              <span className="text-muted-foreground">{displayLabel}</span>
              <span className="ml-auto font-mono font-medium tabular-nums">
                {typeof entry.value === "number" ? entry.value.toLocaleString() : entry.value}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ChartTooltip(props: React.ComponentProps<typeof Tooltip>) {
  return <Tooltip cursor={false} content={<ChartTooltipContent />} {...props} />;
}

// ── Chart legend ────────────────────────────────────────────────────────────

interface ChartLegendContentProps {
  payload?: Array<{
    value: string;
    color: string;
    dataKey?: string;
  }>;
  config?: ChartConfig;
}

function ChartLegendContent({ payload, config }: ChartLegendContentProps) {
  if (!payload?.length) return null;

  return (
    <div className="flex items-center justify-center gap-4 pt-3">
      {payload.map((entry, index) => {
        const key = entry.dataKey ?? entry.value;
        const configEntry = config?.[key];
        const label = configEntry?.label ?? entry.value;

        return (
          <div key={index} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            {label}
          </div>
        );
      })}
    </div>
  );
}

function ChartLegend(props: React.ComponentProps<typeof Legend>) {
  return <Legend content={<ChartLegendContent />} {...props} />;
}

export {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
};
{% endraw %}
