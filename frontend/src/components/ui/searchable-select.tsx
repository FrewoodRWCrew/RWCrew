"use client";

// The app's one single-choice dropdown: a button showing the current choice
// that opens a list with a search box on top. Used on every screen, desktop
// and phone, so all dropdowns search and behave the same way. For picking
// several values use TagMultiSelect; for "search and add a line" use Typeahead.

import { useMemo, useState, type ReactNode } from "react";
import { Combobox as ComboboxPrimitive } from "@base-ui/react/combobox";
import { CheckIcon, ChevronDownIcon, SearchIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

export interface SearchableSelectOption {
  value: string;
  /** The text shown and searched in. */
  label: string;
  /** Richer row content (e.g. a colour swatch); the label stays the searched text. */
  content?: ReactNode;
  disabled?: boolean;
}

interface SearchableSelectProps {
  value: string | null | undefined;
  /** Called with the picked option's value; picking the current one changes nothing. */
  onValueChange?: (value: string | null) => void;
  options: SearchableSelectOption[];
  /** Shown on the button while nothing is chosen. */
  placeholder?: string;
  /** Custom button text, for when it differs from the option's label. */
  renderValue?: (value: string | null) => ReactNode;
  disabled?: boolean;
  id?: string;
  title?: string;
  className?: string;
  "aria-label"?: string;
  size?: "sm" | "default" | "phone";
}

/** Lowercase without accents, so "cafe" also finds "Café". */
function normalize(text: string) {
  return text
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase();
}

export function SearchableSelect({
  value,
  onValueChange,
  options,
  placeholder,
  renderValue,
  disabled,
  id,
  title,
  className,
  "aria-label": ariaLabel,
  size = "default",
}: SearchableSelectProps) {
  const t = useTranslations("common");
  const [query, setQuery] = useState("");

  const selected = options.find((option) => option.value === value) ?? null;

  // Options that start with the query come first, then the ones containing it.
  const matches = useMemo(() => {
    const needle = normalize(query.trim());
    if (!needle) return options;
    const starting: SearchableSelectOption[] = [];
    const containing: SearchableSelectOption[] = [];
    for (const option of options) {
      const text = normalize(option.label);
      if (text.startsWith(needle)) starting.push(option);
      else if (text.includes(needle)) containing.push(option);
    }
    return [...starting, ...containing];
  }, [options, query]);

  const shownValue = renderValue ? renderValue(value ?? null) : selected?.label;
  const isEmpty = shownValue === undefined || shownValue === null || shownValue === "";

  return (
    <ComboboxPrimitive.Root<SearchableSelectOption>
      items={options}
      filteredItems={matches}
      value={selected}
      disabled={disabled}
      autoHighlight
      inputValue={query}
      onInputValueChange={setQuery}
      itemToStringLabel={(option) => option.label}
      isItemEqualToValue={(item, current) => item.value === current.value}
      onOpenChange={(open) => {
        // Every opening starts with the whole list again.
        if (!open) setQuery("");
      }}
      onValueChange={(option) => {
        if (option) onValueChange?.(option.value);
      }}
    >
      <ComboboxPrimitive.Trigger
        id={id}
        title={title}
        aria-label={ariaLabel}
        data-slot="select-trigger"
        data-size={size}
        className={cn(
          "flex w-fit items-center justify-between gap-1.5 rounded-lg border border-input bg-transparent py-2 pr-2 pl-2.5 text-sm whitespace-nowrap transition-colors outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 data-[size=default]:h-8 data-[size=sm]:h-7 data-[size=sm]:rounded-[min(var(--radius-md),10px)] data-[size=phone]:h-11 data-[size=phone]:w-full data-[size=phone]:rounded-md data-[size=phone]:text-base dark:bg-input/30 dark:hover:bg-input/50",
          className,
        )}
      >
        <span
          data-slot="select-value"
          className={cn("line-clamp-1 flex flex-1 items-center gap-1.5 text-left", isEmpty && "text-muted-foreground")}
        >
          {isEmpty ? placeholder : shownValue}
        </span>
        <ChevronDownIcon className="pointer-events-none size-4 shrink-0 text-muted-foreground" />
      </ComboboxPrimitive.Trigger>

      <ComboboxPrimitive.Portal>
        <ComboboxPrimitive.Positioner side="bottom" align="start" sideOffset={4} className="isolate z-50">
          <ComboboxPrimitive.Popup
            data-slot="select-content"
            className="flex max-h-[min(var(--available-height),24rem)] w-max max-w-[min(calc(100vw-2rem),32rem)] min-w-[max(var(--anchor-width),12rem)] origin-(--transform-origin) flex-col overflow-hidden rounded-lg bg-popover text-popover-foreground shadow-md ring-1 ring-foreground/10 duration-100 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95"
          >
            <div className="flex items-center gap-2 border-b px-2.5">
              <SearchIcon className="size-4 shrink-0 text-muted-foreground" />
              {/* text-base on phones: a smaller font makes iOS zoom the page on focus. */}
              <ComboboxPrimitive.Input
                placeholder={t("dropdownSearch")}
                className="h-9 w-full min-w-0 bg-transparent text-base outline-none placeholder:text-muted-foreground md:text-sm"
              />
            </div>
            <ComboboxPrimitive.Empty className="px-2.5 py-2 text-sm text-muted-foreground empty:hidden">
              {t("dropdownNoResults")}
            </ComboboxPrimitive.Empty>
            <ComboboxPrimitive.List className="min-h-0 flex-1 scroll-py-1 overflow-y-auto p-1 empty:hidden">
              {(option: SearchableSelectOption) => (
                <ComboboxPrimitive.Item
                  key={option.value}
                  value={option}
                  disabled={option.disabled}
                  data-slot="select-item"
                  className={cn(
                    "relative flex w-full cursor-default items-center gap-2 rounded-md py-1 pr-8 pl-1.5 text-sm outline-hidden select-none data-disabled:pointer-events-none data-disabled:opacity-50 data-highlighted:bg-accent data-highlighted:text-accent-foreground",
                    size === "phone" && "py-2.5 text-base",
                  )}
                >
                  <span className="min-w-0 flex-1 truncate">{option.content ?? option.label}</span>
                  <ComboboxPrimitive.ItemIndicator className="pointer-events-none absolute right-2 flex size-4 items-center justify-center">
                    <CheckIcon className="size-4" />
                  </ComboboxPrimitive.ItemIndicator>
                </ComboboxPrimitive.Item>
              )}
            </ComboboxPrimitive.List>
          </ComboboxPrimitive.Popup>
        </ComboboxPrimitive.Positioner>
      </ComboboxPrimitive.Portal>
    </ComboboxPrimitive.Root>
  );
}
