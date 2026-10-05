"use client";

// A small "type a few letters, pick from the list" search box, used by
// StockMaster for products (showing their stock and bin) and kars (typing
// a kar number). Keyboard friendly: arrows move through the matches, Enter
// picks the highlighted one (or the only/exact match), Esc closes the list.
// After a pick the box empties again, ready for the next search.

import { forwardRef, useId, useMemo, useState, type ReactNode } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/** How many matches the list shows at most. */
const MAX_MATCHES = 8;

interface TypeaheadProps<T> {
  items: T[];
  getKey: (item: T) => number;
  /** The text searched in (and the "exact match" for Enter). */
  getText: (item: T) => string;
  renderItem: (item: T) => ReactNode;
  onSelect: (item: T) => void;
  placeholder: string;
  emptyText: string;
  /** Items that are listed but can't be picked (e.g. a blocked product). */
  isDisabled?: (item: T) => boolean;
  autoFocus?: boolean;
  disabled?: boolean;
  id?: string;
}

function TypeaheadInner<T>(
  { items, getKey, getText, renderItem, onSelect, placeholder, emptyText, isDisabled, autoFocus, disabled, id }: TypeaheadProps<T>,
  ref: React.ForwardedRef<HTMLInputElement>,
) {
  const listId = useId();
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);

  // Matches that start with the query come first, then the ones containing it.
  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return items.slice(0, MAX_MATCHES);
    const starting: T[] = [];
    const containing: T[] = [];
    for (const item of items) {
      const text = getText(item).toLowerCase();
      if (text.startsWith(needle)) starting.push(item);
      else if (text.includes(needle)) containing.push(item);
    }
    return [...starting, ...containing].slice(0, MAX_MATCHES);
  }, [items, query, getText]);

  function pick(item: T | undefined) {
    if (!item || isDisabled?.(item)) return;
    onSelect(item);
    setQuery("");
    setIsOpen(false);
    setHighlight(0);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setIsOpen(true);
      setHighlight((current) => Math.min(current + 1, matches.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlight((current) => Math.max(current - 1, 0));
    } else if (event.key === "Enter" && !event.ctrlKey && !event.metaKey) {
      if (!query.trim()) return;
      event.preventDefault();
      // An exact match (e.g. a full kar number) wins over the highlight.
      const exact = matches.find((item) => getText(item).toLowerCase() === query.trim().toLowerCase());
      pick(exact ?? matches[highlight]);
    } else if (event.key === "Escape") {
      setIsOpen(false);
    }
  }

  return (
    <div className="relative">
      <Input
        id={id}
        ref={ref}
        value={query}
        placeholder={placeholder}
        autoFocus={autoFocus}
        disabled={disabled}
        autoComplete="off"
        role="combobox"
        aria-expanded={isOpen}
        aria-controls={listId}
        onChange={(event) => {
          setQuery(event.target.value);
          setIsOpen(true);
          setHighlight(0);
        }}
        onFocus={() => setIsOpen(true)}
        // Let a click on a match land before the list closes.
        onBlur={() => window.setTimeout(() => setIsOpen(false), 150)}
        onKeyDown={handleKeyDown}
      />
      {isOpen && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-40 mt-1 max-h-80 w-full overflow-y-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
        >
          {matches.length === 0 && <li className="px-3 py-2 text-sm text-muted-foreground">{emptyText}</li>}
          {matches.map((item, index) => {
            const itemDisabled = isDisabled?.(item) ?? false;
            return (
              <li
                key={getKey(item)}
                role="option"
                aria-selected={index === highlight}
                aria-disabled={itemDisabled}
                className={cn(
                  "cursor-pointer rounded-sm px-3 py-2 text-sm",
                  index === highlight && "bg-accent text-accent-foreground",
                  itemDisabled && "cursor-not-allowed opacity-50",
                )}
                onMouseEnter={() => setHighlight(index)}
                onMouseDown={(event) => {
                  // Keep the focus in the input.
                  event.preventDefault();
                  pick(item);
                }}
              >
                {renderItem(item)}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** forwardRef with generics: the ref reaches the input, so a screen can put
 *  the cursor back in the search after adding a line. */
export const Typeahead = forwardRef(TypeaheadInner) as <T>(
  props: TypeaheadProps<T> & { ref?: React.Ref<HTMLInputElement> },
) => ReturnType<typeof TypeaheadInner>;
