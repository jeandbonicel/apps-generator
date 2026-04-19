"use client";

import * as React from "react";
import { Check, ChevronsUpDown, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "./badge";
import { Button } from "./button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "./command";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";

export interface MultiSelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface MultiSelectProps {
  options: MultiSelectOption[];
  value?: string[];
  onChange?: (value: string[]) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
  name?: string;
}

/**
 * Multi-selection typeahead built from Command + Popover + Badge.
 *
 * Mirrors the Combobox API but keeps ``value`` as a ``string[]``. Clicking
 * an option toggles its membership; already-selected values render as
 * removable badges inside the trigger so the current selection is always
 * visible without opening the dropdown. Suitable for short-to-medium
 * option lists (e.g. enum-backed ``enumArray`` form fields in generated
 * pages).
 */
const MultiSelect = React.forwardRef<HTMLButtonElement, MultiSelectProps>(
  (
    {
      options,
      value = [],
      onChange,
      placeholder = "Select...",
      searchPlaceholder = "Search...",
      emptyText = "No results.",
      disabled,
      className,
      id,
      name,
    },
    ref,
  ) => {
    const [open, setOpen] = React.useState(false);
    const selected = new Set(value);

    const toggle = (v: string) => {
      const next = new Set(selected);
      if (next.has(v)) next.delete(v);
      else next.add(v);
      onChange?.(Array.from(next));
    };

    const remove = (v: string) => {
      onChange?.(value.filter((x) => x !== v));
    };

    const selectedOptions = options.filter((o) => selected.has(o.value));

    return (
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            ref={ref}
            id={id}
            name={name}
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled}
            className={cn(
              "h-auto min-h-10 w-full justify-between font-normal flex-wrap py-1.5",
              className,
            )}
          >
            <div className="flex flex-wrap gap-1 items-center">
              {selectedOptions.length === 0 ? (
                <span className="text-muted-foreground">{placeholder}</span>
              ) : (
                selectedOptions.map((opt) => (
                  <Badge key={opt.value} variant="secondary" className="gap-1">
                    {opt.label}
                    <span
                      role="button"
                      tabIndex={0}
                      aria-label={`Remove ${opt.label}`}
                      className="rounded-sm hover:bg-muted-foreground/20 focus:outline-none"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          e.stopPropagation();
                          remove(opt.value);
                        }
                      }}
                      onMouseDown={(e) => {
                        // mouseDown fires before PopoverTrigger's click — stop
                        // the event so we don't toggle the dropdown open/close
                        // as a side effect of removing a badge.
                        e.preventDefault();
                        e.stopPropagation();
                        remove(opt.value);
                      }}
                    >
                      <X className="h-3 w-3" />
                    </span>
                  </Badge>
                ))
              )}
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
          <Command>
            <CommandInput placeholder={searchPlaceholder} />
            <CommandList>
              <CommandEmpty>{emptyText}</CommandEmpty>
              <CommandGroup>
                {options.map((opt) => (
                  <CommandItem
                    key={opt.value}
                    value={opt.label}
                    disabled={opt.disabled}
                    onSelect={() => toggle(opt.value)}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selected.has(opt.value) ? "opacity-100" : "opacity-0",
                      )}
                    />
                    {opt.label}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    );
  },
);
MultiSelect.displayName = "MultiSelect";

export { MultiSelect };
