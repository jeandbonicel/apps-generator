{% raw %}
import type { Meta, StoryObj } from "@storybook/react";
import {
  Bar,
  BarChart,
  Line,
  LineChart,
  Pie,
  PieChart,
  Area,
  AreaChart,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
} from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartLegend,
  type ChartConfig,
} from "../src";

const meta: Meta<typeof ChartContainer> = {
  title: "Components/Chart",
  component: ChartContainer,
  tags: ["autodocs"],
  decorators: [
    (Story) => (
      <div className="w-full max-w-2xl">
        <Story />
      </div>
    ),
  ],
};

export default meta;
type Story = StoryObj<typeof ChartContainer>;

const barData = [
  { month: "Jan", revenue: 4000, users: 240 },
  { month: "Feb", revenue: 3000, users: 139 },
  { month: "Mar", revenue: 5000, users: 380 },
  { month: "Apr", revenue: 4500, users: 290 },
  { month: "May", revenue: 6000, users: 420 },
  { month: "Jun", revenue: 5500, users: 380 },
];

const barConfig: ChartConfig = {
  revenue: { label: "Revenue", color: "hsl(var(--chart-1))" },
  users: { label: "Users", color: "hsl(var(--chart-2))" },
};

export const BarChartExample: Story = {
  render: () => (
    <ChartContainer config={barConfig}>
      <BarChart data={barData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis />
        <ChartTooltip />
        <ChartLegend />
        <Bar dataKey="revenue" fill="var(--color-revenue)" radius={[4, 4, 0, 0]} />
        <Bar dataKey="users" fill="var(--color-users)" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ChartContainer>
  ),
};

const lineData = [
  { month: "Jan", desktop: 186, mobile: 80 },
  { month: "Feb", desktop: 305, mobile: 200 },
  { month: "Mar", desktop: 237, mobile: 120 },
  { month: "Apr", desktop: 273, mobile: 190 },
  { month: "May", desktop: 409, mobile: 330 },
  { month: "Jun", desktop: 214, mobile: 140 },
];

const lineConfig: ChartConfig = {
  desktop: { label: "Desktop", color: "hsl(var(--chart-1))" },
  mobile: { label: "Mobile", color: "hsl(var(--chart-2))" },
};

export const LineChartExample: Story = {
  render: () => (
    <ChartContainer config={lineConfig}>
      <LineChart data={lineData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis />
        <ChartTooltip />
        <ChartLegend />
        <Line
          type="monotone"
          dataKey="desktop"
          stroke="var(--color-desktop)"
          strokeWidth={2}
        />
        <Line
          type="monotone"
          dataKey="mobile"
          stroke="var(--color-mobile)"
          strokeWidth={2}
        />
      </LineChart>
    </ChartContainer>
  ),
};

const pieData = [
  { name: "Chrome", value: 275 },
  { name: "Safari", value: 200 },
  { name: "Firefox", value: 187 },
  { name: "Edge", value: 173 },
  { name: "Other", value: 90 },
];

const COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

const pieConfig: ChartConfig = {
  chrome: { label: "Chrome", color: "hsl(var(--chart-1))" },
  safari: { label: "Safari", color: "hsl(var(--chart-2))" },
  firefox: { label: "Firefox", color: "hsl(var(--chart-3))" },
  edge: { label: "Edge", color: "hsl(var(--chart-4))" },
  other: { label: "Other", color: "hsl(var(--chart-5))" },
};

export const PieChartExample: Story = {
  render: () => (
    <ChartContainer config={pieConfig}>
      <PieChart>
        <ChartTooltip />
        <Pie
          data={pieData}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={80}
          paddingAngle={5}
          dataKey="value"
        >
          {pieData.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <ChartLegend />
      </PieChart>
    </ChartContainer>
  ),
};

const areaData = [
  { month: "Jan", total: 1200, recurring: 900 },
  { month: "Feb", total: 1900, recurring: 1200 },
  { month: "Mar", total: 1600, recurring: 1100 },
  { month: "Apr", total: 2400, recurring: 1800 },
  { month: "May", total: 2800, recurring: 2100 },
  { month: "Jun", total: 3200, recurring: 2500 },
];

const areaConfig: ChartConfig = {
  total: { label: "Total Revenue", color: "hsl(var(--chart-1))" },
  recurring: { label: "Recurring", color: "hsl(var(--chart-2))" },
};

export const AreaChartExample: Story = {
  render: () => (
    <ChartContainer config={areaConfig}>
      <AreaChart data={areaData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" />
        <YAxis />
        <ChartTooltip />
        <ChartLegend />
        <Area
          type="monotone"
          dataKey="total"
          stroke="var(--color-total)"
          fill="var(--color-total)"
          fillOpacity={0.3}
        />
        <Area
          type="monotone"
          dataKey="recurring"
          stroke="var(--color-recurring)"
          fill="var(--color-recurring)"
          fillOpacity={0.3}
        />
      </AreaChart>
    </ChartContainer>
  ),
};
{% endraw %}
