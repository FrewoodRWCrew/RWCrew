"use client";

// A reusable multi-select "tag picker": selected options render as removable
// chips, and typing into the inline text box filters the remaining options
// into a small suggestion list below. No popover/combobox library is used
// here on purpose — this codebase doesn't have one, so this is built from
// plain primitives (Badge for chips, a bare input, a conditionally-rendered
// suggestion div) the same conservative way the rest of the UI is built.

import { useRef, useState } from "react";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export interface TagMultiSelectOption {
  id: number;
  label: string;
}

interface TagMultiSelectProps {
  id?: string;
  options: TagMultiSelectOption[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
  placeholder?: string;
  disabled?: boolean;
}

// Cap the suggestion list so it never grows into an unusably long dropdown.
const MAX_SUGGESTIONS = 8;

export function TagMultiSelect({ id, options, selectedIds, onChange, placeholder, disabled }: TagMultiSelectProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedSuggestionIndex, setHighlightedSuggestionIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const selectedOptions = options.filter((option) => selectedIds.includes(option.id));
  const filteredSuggestions = options
    .filter((option) => !selectedIds.includes(option.id))
    .filter((option) => option.label.toLowerCase().includes(query.trim().toLowerCase()))
    .slice(0, MAX_SUGGESTIONS);

  function removeOption(optionId: number) {
    onChange(selectedIds.filter((selectedId) => selectedId !== optionId));
  }

  function addOption(optionId: number) {
    onChange([...selectedIds, optionId]);
    setQuery("");
    inputRef.current?.focus();
  }

  return (
    <div className="relative">
      <div
        className={cn(
          "flex min-h-8 flex-wrap items-center gap-1 rounded-lg border border-input bg-transparent px-2 py-1",
          disabled && "opacity-50",
        )}
        onClick={() => inputRef.current?.focus()}
      >
        {selectedOptions.map((option) => (
          <Badge key={option.id} variant="secondary" className="gap-1">
            {option.label}
            <button
              type="button"
              aria-label={`Remove ${option.label}`}
              disabled={disabled}
              onClick={() => removeOption(option.id)}
              className="rounded-full hover:bg-muted-foreground/20"
            >
              <X className="size-3" />
            </button>
          </Badge>
        ))}
        <input
          ref={inputRef}
          id={id}
          type="text"
          disabled={disabled}
          value={query}
          placeholder={selectedOptions.length === 0 ? placeholder : undefined}
          onChange={(event) => {
            setQuery(event.target.value);
            setHighlightedSuggestionIndex(0);
            setIsOpen(true);
          }}
          onFocus={() => {
            setHighlightedSuggestionIndex(0);
            setIsOpen(true);
          }}
          onBlur={() => setIsOpen(false)}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setHighlightedSuggestionIndex((current) =>
                filteredSuggestions.length === 0 ? 0 : Math.min(current + 1, filteredSuggestions.length - 1),
              );
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setHighlightedSuggestionIndex((current) => Math.max(current - 1, 0));
            } else if (event.key === "Enter" && filteredSuggestions[highlightedSuggestionIndex]) {
              event.preventDefault();
              addOption(filteredSuggestions[highlightedSuggestionIndex].id);
            } else if (event.key === "Escape") {
              event.preventDefault();
              setQuery("");
              setIsOpen(false);
            }
          }}
          className="min-w-24 flex-1 border-0 bg-transparent p-1 text-sm outline-none placeholder:text-muted-foreground"
        />
      </div>

      {isOpen && filteredSuggestions.length > 0 && (
        <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-48 overflow-auto rounded-md border bg-popover shadow-md">
          {filteredSuggestions.map((option, index) => (
            <div
              key={option.id}
              role="option"
              // mousedown fires before blur, so preventing its default here
              // stops the input from ever losing focus — the click below
              // then still runs with the suggestion list still open.
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => addOption(option.id)}
              onMouseEnter={() => setHighlightedSuggestionIndex(index)}
              aria-selected={index === highlightedSuggestionIndex}
              className={cn(
                "cursor-pointer px-2 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground",
                index === highlightedSuggestionIndex && "bg-accent text-accent-foreground",
              )}
            >
              {option.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
