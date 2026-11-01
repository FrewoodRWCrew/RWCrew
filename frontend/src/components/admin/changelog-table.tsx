"use client";

// The super admin's "Wijzigingen" screen: a read-only list of every update,
// correction and new functionality, newest on top (the backend sorts it, see
// backend/app/landing/changelog.py). All filtering happens here in the browser.

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { formatDateNl } from "@/lib/date-time";
import type { ChangelogEntry } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

// The dropdowns' "no filter" value.
const ALL = "all";

// Translation key per line type and status.
const TYPE_LABEL_KEYS = {
  feature: "typeFeature",
  update: "typeUpdate",
  fix: "typeFix",
} as const satisfies Record<ChangelogEntry["type"], string>;

const STATUS_LABEL_KEYS = {
  open: "statusOpen",
  in_progress: "statusInProgress",
  done: "statusDone",
} as const satisfies Record<ChangelogEntry["status"], string>;

const COLUMN_COUNT = 8;

const HEAD_CLASS = "sticky top-0 z-20 bg-background font-bold underline";

interface FilterSelectProps {
  id: string;
  label: string;
  value: string;
  allLabel: string;
  // Dropdown options as [value, shown text].
  options: [string, string][];
  onChange: (value: string) => void;
}

/** One labelled dropdown of the filter row, with "All" as its first option. */
function FilterSelect({ id, label, value, allLabel, options, onChange }: FilterSelectProps) {
  const optionLabels = new Map(options);

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <SearchableSelect
        value={value}
        onValueChange={(next) => onChange(next ?? ALL)}
        id={id}
        className="min-w-44"
        renderValue={(current: string | null) => optionLabels.get(current ?? ALL) ?? allLabel}
        options={[
          { value: ALL, label: allLabel },
          ...options.map(([optionValue, optionLabel]) => ({ value: optionValue, label: optionLabel })),
        ]}
      />
    </div>
  );
}

interface ChangelogTableProps {
  // null = the shared list couldn't be fetched.
  entries: ChangelogEntry[] | null;
}

export function ChangelogTable({ entries }: ChangelogTableProps) {
  const t = useTranslations("admin.changelog");
  const [typeFilter, setTypeFilter] = useState(ALL);
  const [statusFilter, setStatusFilter] = useState(ALL);
  const [moduleFilter, setModuleFilter] = useState(ALL);
  const [search, setSearch] = useState("");

  const lines = useMemo(() => entries ?? [], [entries]);

  // The module dropdown only offers modules that have a line.
  const moduleOptions = useMemo(
    () => [...new Set(lines.map((line) => line.module))].sort((a, b) => a.localeCompare(b)),
    [lines],
  );

  // Filtering keeps the backend's order, so the newest line stays on top.
  const shownLines = useMemo(() => {
    const searchText = search.trim().toLowerCase();
    return lines.filter((line) => {
      if (typeFilter !== ALL && line.type !== typeFilter) return false;
      if (statusFilter !== ALL && line.status !== statusFilter) return false;
      if (moduleFilter !== ALL && line.module !== moduleFilter) return false;
      const lineText = [...line.issues, line.title, line.description, ...line.commits].join(" ").toLowerCase();
      return lineText.includes(searchText);
    });
  }, [lines, typeFilter, statusFilter, moduleFilter, search]);

  const anyFilterSet = typeFilter !== ALL || statusFilter !== ALL || moduleFilter !== ALL || search !== "";

  function handleClearFilters() {
    setTypeFilter(ALL);
    setStatusFilter(ALL);
    setModuleFilter(ALL);
    setSearch("");
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      {entries === null ? (
        <p className="text-sm text-destructive">{t("unavailable")}</p>
      ) : (
        <>
          <div className="flex flex-wrap items-end gap-4">
            <FilterSelect
              id="changelog-type"
              label={t("columnType")}
              value={typeFilter}
              allLabel={t("all")}
              options={Object.entries(TYPE_LABEL_KEYS).map(([value, key]) => [value, t(key)])}
              onChange={setTypeFilter}
            />
            <FilterSelect
              id="changelog-status"
              label={t("columnStatus")}
              value={statusFilter}
              allLabel={t("all")}
              options={Object.entries(STATUS_LABEL_KEYS).map(([value, key]) => [value, t(key)])}
              onChange={setStatusFilter}
            />
            <FilterSelect
              id="changelog-module"
              label={t("columnModule")}
              value={moduleFilter}
              allLabel={t("all")}
              options={moduleOptions.map((module) => [module, module])}
              onChange={setModuleFilter}
            />
            <div className="flex min-w-64 flex-1 flex-col gap-2">
              <Label htmlFor="changelog-search">{t("filterSearch")}</Label>
              <Input
                id="changelog-search"
                value={search}
                placeholder={t("searchPlaceholder")}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
            {anyFilterSet && (
              <Button variant="ghost" onClick={handleClearFilters}>
                {t("clearFilters")}
              </Button>
            )}
          </div>

          <p className="text-sm text-muted-foreground">{t("shown", { shown: shownLines.length, total: lines.length })}</p>

          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className={HEAD_CLASS}>{t("columnDate")}</TableHead>
                  <TableHead className={HEAD_CLASS}>{t("columnNumber")}</TableHead>
                  <TableHead className={HEAD_CLASS}>{t("columnType")}</TableHead>
                  <TableHead className={HEAD_CLASS}>{t("columnModule")}</TableHead>
                  <TableHead className={HEAD_CLASS}>{t("columnTitle")}</TableHead>
                  <TableHead className={HEAD_CLASS}>{t("columnDescription")}</TableHead>
                  <TableHead className={HEAD_CLASS}>{t("columnStatus")}</TableHead>
                  <TableHead className={HEAD_CLASS}>{t("columnCommit")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {shownLines.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={COLUMN_COUNT} className="text-center text-muted-foreground">
                      {lines.length === 0 ? t("empty") : t("noResults")}
                    </TableCell>
                  </TableRow>
                )}
                {shownLines.map((line) => (
                  <TableRow key={line.id}>
                    <TableCell className="align-top whitespace-nowrap">{formatDateNl(line.date)}</TableCell>
                    <TableCell className="align-top whitespace-nowrap">
                      {line.issues.length > 0 ? line.issues.join(", ") : <span className="text-muted-foreground">—</span>}
                    </TableCell>
                    <TableCell className="align-top">
                      <Badge variant={line.type === "fix" ? "secondary" : "outline"}>{t(TYPE_LABEL_KEYS[line.type])}</Badge>
                    </TableCell>
                    <TableCell className="align-top">{line.module}</TableCell>
                    <TableCell className="min-w-64 align-top font-medium whitespace-normal">{line.title}</TableCell>
                    <TableCell className="min-w-96 align-top whitespace-normal text-muted-foreground">
                      {line.description}
                    </TableCell>
                    <TableCell className="align-top">
                      <Badge variant={line.status === "done" ? "secondary" : "default"}>
                        {t(STATUS_LABEL_KEYS[line.status])}
                      </Badge>
                    </TableCell>
                    {/* Full hashes, one per line; "—" until the work is committed. */}
                    <TableCell className="align-top font-mono text-xs">
                      {line.commits.length > 0 ? (
                        line.commits.map((commit) => <div key={commit}>{commit}</div>)
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </div>
  );
}
