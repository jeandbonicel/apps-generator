import type { Meta, StoryObj } from "@storybook/react";
import { Toast, ToastTitle, ToastDescription } from "../src";

const meta: Meta<typeof Toast> = {
  title: "Components/Toast",
  component: Toast,
  tags: ["autodocs"],
  argTypes: {
    variant: {
      control: "select",
      options: ["default", "destructive", "success"],
    },
  },
};

export default meta;
type Story = StoryObj<typeof Toast>;

export const Default: Story = {
  render: () => (
    <Toast>
      <ToastTitle>Notification</ToastTitle>
      <ToastDescription>Something happened that you should know about.</ToastDescription>
    </Toast>
  ),
};

export const Destructive: Story = {
  render: () => (
    <Toast variant="destructive">
      <ToastTitle>Error</ToastTitle>
      <ToastDescription>Something went wrong. Please try again.</ToastDescription>
    </Toast>
  ),
};

export const Success: Story = {
  render: () => (
    <Toast variant="success">
      <ToastTitle>Success</ToastTitle>
      <ToastDescription>Your changes have been saved.</ToastDescription>
    </Toast>
  ),
};

export const WithClose: Story = {
  render: () => (
    <Toast onClose={() => alert("closed")}>
      <ToastTitle>Dismissible</ToastTitle>
      <ToastDescription>Click the X to dismiss this toast.</ToastDescription>
    </Toast>
  ),
};
