import type { Meta, StoryObj } from "@storybook/react";
import {
  Accordion, AccordionItem, AccordionTrigger, AccordionContent,
} from "../src";

const meta: Meta<typeof Accordion> = {
  title: "Components/Accordion",
  component: Accordion,
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof Accordion>;

export const Default: Story = {
  render: () => (
    <Accordion type="single" collapsible className="w-80">
      <AccordionItem value="item-1">
        <AccordionTrigger>Is it accessible?</AccordionTrigger>
        <AccordionContent>Yes. Built on Radix primitives, follows WAI-ARIA.</AccordionContent>
      </AccordionItem>
      <AccordionItem value="item-2">
        <AccordionTrigger>Is it styled?</AccordionTrigger>
        <AccordionContent>Yes. Tailwind + shadcn theme, ready to use.</AccordionContent>
      </AccordionItem>
      <AccordionItem value="item-3">
        <AccordionTrigger>Is it animated?</AccordionTrigger>
        <AccordionContent>Yes. Uses CSS keyframes for open/close transitions.</AccordionContent>
      </AccordionItem>
    </Accordion>
  ),
};
