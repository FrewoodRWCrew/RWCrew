"use client";

// "Copy from last season" panel shown above a Ploeg Wizard step whose
// backend definition offers it (step.copy_from_previous, see
// backend/app/modules/module_8/previous_season.py). It lists last season's
// values line by line with a checkbox each; every line that would change
// something starts ticked, so when nothing changed one click on "Copy"
// takes it all over. Lines that are already present, or can't be copied
// (e.g. the festival isn't selected this season), are shown but disabled.

import { useState } from "react";
import { ChevronDown, ChevronRight, Copy } from "lucide-react";
import { useTranslations } from "next-intl";
import { getAltsienSelectPreviousSeason } from "@/lib/api";
import type { AltsienSelectPreviousLine, AltsienSelectPreviousSeason } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useKeyedLoad } from "@/components/module-8/use-keyed-load";

interface CopyPreviousSeasonProps {
  teamId: number;
  seasonId: number;
  stepKey: string;
  /** True while the wizard is saving/copying; disables the Copy button. */
  disabled: boolean;
  /** Copies the given lines (the wizard first saves the step's draft);
   *  resolves true when the copy succeeded. */
  onCopy: (lineKeys: string[]) => Promise<boolean>;
}

/** A line is worth copying when it can be copied and isn't there yet. */
function isCopyable(line: AltsienSelectPreviousLine) {
  return line.unavailable_reason === null && !line.already_present;
}

export function CopyPreviousSeason({ teamId, seasonId, stepKey, disabled, onCopy }: CopyPreviousSeasonProps) {
  const t = useTranslations("altsienSelect.wizard.previousSeason");
  const previous = useKeyedLoad<AltsienSelectPreviousSeason>(`${seasonId}:${teamId}:${stepKey}`, () =>
    getAltsienSelectPreviousSeason(teamId, seasonId, stepKey),
  );
  // Lines the user un-ticked; everything else that's copyable is ticked.
  const [unticked, setUnticked] = useState<Set<string>>(() => new Set());
  // null = the default: open while there is something to copy.
  const [isOpen, setIsOpen] = useState<boolean | null>(null);

  if (previous.failed) {
    return <p className="text-sm text-destructive">{t("loadError")}</p>;
  }
  // Nothing to show while loading, without an earlier season or when that
  // season had nothing for this step.
  const data = previous.data;
  if (!data || data.previous_season_name === null || data.lines.length === 0) return null;

  const copyable = data.lines.filter(isCopyable);
  const selectedKeys = copyable.filter((line) => !unticked.has(line.key)).map((line) => line.key);
  const allSelected = copyable.length > 0 && selectedKeys.length === copyable.length;
  const open = isOpen ?? copyable.length > 0;

  function toggleLine(key: string, checked: boolean) {
    setUnticked((current) => {
      const next = new Set(current);
      if (checked) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleAll(checked: boolean) {
    setUnticked(checked ? new Set() : new Set(copyable.map((line) => line.key)));
  }

  function toggleOpen() {
    // Opening again re-reads last season, so the flags match what was
    // changed in the step in the meantime.
    if (!open) previous.reload();
    setIsOpen(!open);
  }

  async function handleCopy() {
    if (await onCopy(selectedKeys)) {
      setUnticked(new Set());
      previous.reload();
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-md border border-dashed p-3">
      {/* Header: title + summary, and the show/hide toggle. */}
      <button type="button" onClick={toggleOpen} className="flex items-center justify-between gap-3 text-left">
        <span className="flex flex-col">
          <span className="font-medium">{t("title", { season: data.previous_season_name })}</span>
          <span className="text-sm text-muted-foreground">{t("summary", { count: copyable.length })}</span>
        </span>
        <span className="flex shrink-0 items-center gap-1 text-sm text-muted-foreground">
          {open ? t("hide") : t("show")}
          {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
        </span>
      </button>

      {open && (
        <>
          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-20 w-10 bg-background">
                    <Checkbox
                      checked={allSelected}
                      indeterminate={selectedKeys.length > 0 && !allSelected}
                      disabled={copyable.length === 0}
                      onCheckedChange={(checked) => toggleAll(checked === true)}
                      aria-label={t("selectAll")}
                    />
                  </TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnLine")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnValue")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnStatus")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.lines.map((line) => {
                  const lineCopyable = isCopyable(line);
                  return (
                    <TableRow key={line.key} className="group">
                      <TableCell>
                        <Checkbox
                          checked={lineCopyable && !unticked.has(line.key)}
                          disabled={!lineCopyable}
                          onCheckedChange={(checked) => toggleLine(line.key, checked === true)}
                          aria-label={line.label}
                        />
                      </TableCell>
                      {/* What the line is, and where it lands this season if that differs. */}
                      <TableCell className="max-w-md whitespace-pre-wrap">
                        <span className="font-medium">{line.label}</span>
                        {line.target && <span className="text-muted-foreground"> → {line.target}</span>}
                      </TableCell>
                      {/* Last season's value, plus the current one when it differs. */}
                      <TableCell>
                        {line.detail ?? "—"}
                        {line.current_detail && (
                          <span className="block text-xs text-muted-foreground">
                            {t("now", { value: line.current_detail })}
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        {line.unavailable_reason !== null ? (
                          <Badge variant="outline" className="text-muted-foreground">
                            {t(`reason.${line.unavailable_reason}`)}
                          </Badge>
                        ) : line.already_present ? (
                          <Badge variant="secondary">{t("alreadyPresent")}</Badge>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
          <div>
            <Button variant="outline" disabled={disabled || selectedKeys.length === 0} onClick={handleCopy}>
              <Copy className="size-4" />
              {t("copy", { count: selectedKeys.length })}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
