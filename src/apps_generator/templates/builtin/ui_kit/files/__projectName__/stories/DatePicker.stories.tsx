import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { DatePicker } from "../src";

const meta: Meta<typeof DatePicker> = {
  title: "Components/DatePicker",
  component: DatePicker,
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof DatePicker>;

export const Default: Story = {
  render: () => {
    const [date, setDate] = useState<Date | undefined>();
    return (
      <div className="w-72">
        <DatePicker value={date} onChange={setDate} />
      </div>
    );
  },
};
