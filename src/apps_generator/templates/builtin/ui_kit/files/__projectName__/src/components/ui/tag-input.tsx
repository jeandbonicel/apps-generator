"use client";

import * as React from "react";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";
import { Badge } from "./badge";

export interface TagInputProps {
  value?: string[];
  onChange?: (value: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
  name?: string;
  /** Separator keys that commit the current input as a new tag. Defaults to Enter + comma. */
  separators?: string[];
  /** Optional: drop duplicates silently. Default ``true``. */
  dedupe?: boolean;
}

/**
 * Free-form chip input for building a list of strings.
 *
 * Typing + Enter (or comma) commits the current draft as a new Badge chip;
 * Backspace on an empty input removes the trailing chip. Suitable for
 * ad-hoc tag / keyword lists (the ``stringArray`` form-field type in
 * generated pages). For a fixed option set, reach for ``MultiSelect``
 * instead.
 */
const TagInput = React.forwardRef<HTMLInputElement, TagInputProps>(
  (
    {
      value = [],
      onChange,
      placeholder = "Add and press Enter...",
      disabled,
      className,
      id,
      name,
      separators = ["Enter", ","],
      dedupe = true,
    },
    ref,
  ) => {
    const [draft, setDraft] = React.useState("");

    const addTag = (raw: string) => {
      const tag = raw.trim();
      if (!tag) return;
      if (dedupe && value.includes(tag)) {
        setDraft("");
        return;
      }
      onChange?.([...value, tag]);
      setDraft("");
    };

    const removeTag = (index: number) => {
      onChange?.(value.filter((_, i) => i !== index));
    };

    const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (separators.includes(e.key)) {
        e.preventDefault();
        addTag(draft);
      } else if (e.key === "Backspace" && draft === "" && value.length > 0) {
        // Backspace on empty input peels off the last tag — matches the
        // native chip-input convention.
        e.preventDefault();
        removeTag(value.length - 1);
      }
    };

    return (
      <div
        className={cn(
          "flex flex-wrap gap-1.5 items-center min-h-10 w-full rounded-md border border-input bg-background px-2 py-1.5 text-sm ring-offset-background focus-within:outline-none focus-within:ring-2 focus-within:ring-ring",
          disabled && "opacity-50 pointer-events-none",
          className,
        )}
        onClick={() => {
          // Clicking chrome around the chips focuses the input — feels native
          // without needing a separate label/for wiring.
          const el = document.getElementById(id ?? "") as HTMLInputElement | null;
          el?.focus();
        }}
      >
        {value.map((tag, i) => (
          <Badge key={`${tag}-${i}`} variant="secondary" className="gap-1">
            {tag}
            <button
              type="button"
              aria-label={`Remove ${tag}`}
              className="rounded-sm hover:bg-muted-foreground/20 focus:outline-none focus:ring-1 focus:ring-ring"
              onClick={(e) => {
                e.stopPropagation();
                removeTag(i);
              }}
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        <input
          ref={ref}
          id={id}
          name={name}
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKeyDown}
          onBlur={() => addTag(draft)}
          disabled={disabled}
          placeholder={value.length === 0 ? placeholder : ""}
          className="flex-1 min-w-[120px] bg-transparent outline-none placeholder:text-muted-foreground"
        />
      </div>
    );
  },
);
TagInput.displayName = "TagInput";

export { TagInput };
