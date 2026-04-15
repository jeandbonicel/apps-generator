import type { Meta, StoryObj } from "@storybook/react";
import { Page } from "../src/components/layout/Page";
import { PageHeader } from "../src/components/layout/PageHeader";
import { PageSection } from "../src/components/layout/PageSection";
import { PageGrid } from "../src/components/layout/PageGrid";
import { Button } from "../src/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "../src/components/ui/card";
import { Badge } from "../src/components/ui/badge";

const meta: Meta<typeof Page> = {
  title: "Layout/Page",
  component: Page,
  tags: ["autodocs"],
  parameters: {
    layout: "fullscreen",
  },
};

export default meta;
type Story = StoryObj<typeof Page>;

export const Default: Story = {
  render: () => (
    <Page>
      <PageHeader title="Dashboard" description="Welcome back">
        <Button>New Item</Button>
      </PageHeader>
      <PageSection>
        <PageGrid columns={3}>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Revenue
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">$45,231</p>
              <Badge className="mt-2">+20.1%</Badge>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Active Users
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">2,350</p>
              <Badge variant="secondary" className="mt-2">+180</Badge>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Pending
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">12</p>
              <Badge variant="outline" className="mt-2">-2</Badge>
            </CardContent>
          </Card>
        </PageGrid>
      </PageSection>
      <PageSection title="Recent Activity" description="Last 7 days">
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Activity content goes here...</p>
          </CardContent>
        </Card>
      </PageSection>
    </Page>
  ),
};

export const WithMultipleSections: Story = {
  render: () => (
    <Page>
      <PageHeader title="Orders" description="Manage your orders" />
      <PageSection title="Stats">
        <PageGrid columns={4}>
          <Card><CardContent className="pt-6"><p className="text-2xl font-bold">1,247</p><p className="text-sm text-muted-foreground">Total</p></CardContent></Card>
          <Card><CardContent className="pt-6"><p className="text-2xl font-bold">34</p><p className="text-sm text-muted-foreground">Processing</p></CardContent></Card>
          <Card><CardContent className="pt-6"><p className="text-2xl font-bold">892</p><p className="text-sm text-muted-foreground">Completed</p></CardContent></Card>
          <Card><CardContent className="pt-6"><p className="text-2xl font-bold">$48k</p><p className="text-sm text-muted-foreground">Revenue</p></CardContent></Card>
        </PageGrid>
      </PageSection>
      <PageSection title="Recent Orders">
        <Card>
          <CardContent className="pt-6">
            <p className="text-muted-foreground">Table would go here...</p>
          </CardContent>
        </Card>
      </PageSection>
    </Page>
  ),
};
