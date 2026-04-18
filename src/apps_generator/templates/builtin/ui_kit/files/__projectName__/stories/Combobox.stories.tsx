import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Combobox } from "../src";

const meta: Meta<typeof Combobox> = {
  title: "Components/Combobox",
  component: Combobox,
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj<typeof Combobox>;

const frameworks = [
  { value: "next.js", label: "Next.js" },
  { value: "sveltekit", label: "SvelteKit" },
  { value: "nuxt.js", label: "Nuxt.js" },
  { value: "remix", label: "Remix" },
  { value: "astro", label: "Astro" },
];

export const Default: Story = {
  render: () => {
    const [value, setValue] = useState<string | undefined>();
    return (
      <div className="w-72">
        <Combobox
          options={frameworks}
          value={value}
          onChange={setValue}
          placeholder="Select framework..."
          searchPlaceholder="Search framework..."
          emptyText="No framework found."
        />
      </div>
    );
  },
};
