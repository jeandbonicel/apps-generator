import type { Meta, StoryObj } from "@storybook/react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Form, FormField, FormItem, FormLabel, FormControl, FormDescription, FormMessage,
  Input, Button,
} from "../src";

const meta: Meta = {
  title: "Components/Form",
  tags: ["autodocs"],
};
export default meta;
type Story = StoryObj;

const schema = z.object({
  username: z.string().min(2, "Username must be at least 2 characters."),
  email: z.string().email("Invalid email address."),
});

type FormValues = z.infer<typeof schema>;

export const Default: Story = {
  render: () => {
    const form = useForm<FormValues>({
      resolver: zodResolver(schema),
      defaultValues: { username: "", email: "" },
    });
    return (
      <Form {...form}>
        <form onSubmit={form.handleSubmit((v) => console.log(v))} className="w-80 space-y-6">
          <FormField
            control={form.control}
            name="username"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Username</FormLabel>
                <FormControl>
                  <Input placeholder="jane-doe" {...field} />
                </FormControl>
                <FormDescription>Public display name.</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email</FormLabel>
                <FormControl>
                  <Input type="email" placeholder="jane@example.com" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit">Submit</Button>
        </form>
      </Form>
    );
  },
};
