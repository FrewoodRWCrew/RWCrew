"use client";

// The "one text filter above every column" row of Atelier's list screens
// (Openstaand, Reservaties): the filter state plus the sticky header cell
// that holds one small text field. Filtering is client-side: a row matches
// when every filled-in filter is found (ignoring case) in its column's text.

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { TableHead } from "@/components/ui/table";

/** Case-insensitive substring match; an empty filter matches everything. */
export function textMatches(fieldValue: string | number | null | undefined, filterValue: string): boolean {
  const wanted = filterValue.trim().toLowerCase();
  if (!wanted) return true;
  return String(fieldValue ?? "").toLowerCase().includes(wanted);
}

/** Filter state per column key, with a matcher for one row's column texts. */
export function useColumnFilters<K extends string>() {
  const [filters, setFilters] = useState<Partial<Record<K, string>>>({});

  // Change one column's filter text.
  function setFilter(key: K, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  // A row matches when each filled-in filter is found in its column's text.
  function matches(values: Partial<Record<K, string | number | null | undefined>>): boolean {
    return (Object.keys(filters) as K[]).every((key) => textMatches(values[key], filters[key] ?? ""));
  }

  // Whether any filter is filled in (to show "x of y shown" hints).
  const active = Object.values<string | undefined>(filters).some((value) => (value ?? "").trim() !== "");

  return { filters, setFilter, matches, active };
}

interface FilterHeadCellProps {
  label: string;
  value: string | undefined;
  onChange: (value: string) => void;
  className?: string;
}

/** A second-header-row cell (sticky below the headings) holding one text filter. */
export function FilterHeadCell({ label, value, onChange, className }: FilterHeadCellProps) {
  return (
    <TableHead className={`sticky top-10 z-20 bg-background ${className ?? ""}`}>
      <Input
        aria-label={label}
        placeholder={label}
        className="h-8 w-full min-w-24 font-normal"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      />
    </TableHead>
  );
}
