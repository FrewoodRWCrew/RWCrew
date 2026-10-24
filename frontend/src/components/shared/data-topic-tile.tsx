"use client";

// One tile on a module's "Data Upload/Download" grid, plus the row-result
// types its upload shows: a button styled as an outlined card (the
// module's own accent colour as the border) that opens a dialog with that
// table's template download / bulk upload / export tools. Shared by
// MasterData's grid (components/module-9/masterdata-data-upload-download.tsx)
// and StockMaster's product grid (components/module-4/product-data-upload-download.tsx);
// KarTracker keeps its own older copy (components/module-2/kar-data-upload-download.tsx).

import { useState } from "react";
import { type LucideIcon } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";
import type { MasterDataImportOutcome } from "@/lib/types";
import { getModuleTheme } from "@/lib/module-theme";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/** One row's outcome, normalized to a common shape regardless of which
 * table's own wire type it came from — each tile wrapper below maps its
 * own "key" field (name/location/delivery_method/team_tasks) into this
 * before handing it to the shared dialog.
 */
export interface ImportRowResult {
  row_number: number;
  key: string | null;
  outcome: MasterDataImportOutcome;
  detail: string | null;
}

/** How many rows of an upload ended in each outcome (the summary line). */
export type ImportCounts = Record<"created" | "updated" | "unchanged" | "errors", number>;

const OUTCOME_BADGE_VARIANT: Record<
  MasterDataImportOutcome,
  "default" | "secondary" | "outline" | "destructive"
> = {
  created: "default",
  updated: "secondary",
  unchanged: "outline",
  error: "destructive",
};

export interface DataTopicTileProps {
  /** The module whose accent colour the tile uses, e.g. "module-9". */
  moduleKey: string;
  icon: LucideIcon;
  tileTitle: string;
  dialogTitle: string;
  dialogDescription: string;
  /** How the upload treats existing records (shown under the description). */
  hint: string;
  templateUrl: string;
  exportUrl: string;
  downloadTemplateLabel: string;
  downloadTemplateButton: string;
  /** Whether the current user has "create" permission — hides the file
   * input/upload button (in favour of an explanatory note) when false. */
  canUpload: boolean;
  uploadNotAllowed: string;
  chooseFileLabel: string;
  uploadButton: string;
  importFailed: string;
  importSummary: (counts: ImportCounts) => string;
  importColumnRow: string;
  importColumnKey: string;
  importColumnOutcome: string;
  importColumnDetail: string;
  importOutcomeLabel: (outcome: ImportRowResult["outcome"]) => string;
  exportLabel: string;
  exportButton: string;
  onUpload: (file: File) => Promise<ImportRowResult[]>;
}

/**
 * One tile on a Data Upload/Download grid: a button styled as an outlined
 * card (the module's own accent colour as the border, not a solid fill)
 * that opens a dialog with that table's template download / bulk upload /
 * export tools.
 */
export function DataTopicTile({
  moduleKey,
  icon: Icon,
  tileTitle,
  dialogTitle,
  dialogDescription,
  hint,
  templateUrl,
  exportUrl,
  downloadTemplateLabel,
  downloadTemplateButton,
  canUpload,
  uploadNotAllowed,
  chooseFileLabel,
  uploadButton,
  importFailed,
  importSummary,
  importColumnRow,
  importColumnKey,
  importColumnOutcome,
  importColumnDetail,
  importOutcomeLabel,
  exportLabel,
  exportButton,
  onUpload,
}: DataTopicTileProps) {
  const { accentColorToken } = getModuleTheme(moduleKey);
  const accentColor = `var(--color-${accentColorToken})`;

  const [isOpen, setIsOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [results, setResults] = useState<ImportRowResult[] | null>(null);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from a clean slate each time the dialog is opened, so a
      // previous import's results don't linger behind a new file pick.
      setFile(null);
      setResults(null);
    }
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    // Picking a different file always clears any displayed results — they
    // describe the previous file's outcome, not this one, so leaving them
    // up would make it look like they belong to the newly picked file.
    setFile(event.target.files?.[0] ?? null);
    setResults(null);
  }

  async function handleUpload() {
    if (!file) return;

    // Clear out the previous upload's results immediately, so a slow or
    // failed request never leaves stale success/error rows on screen
    // looking like they belong to the file just picked.
    setResults(null);
    setIsUploading(true);
    try {
      setResults(await onUpload(file));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : importFailed;
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  // Counts per outcome, for the summary line above the results table.
  const countOf = (outcome: MasterDataImportOutcome) => results?.filter((row) => row.outcome === outcome).length ?? 0;
  const counts: ImportCounts = {
    created: countOf("created"),
    updated: countOf("updated"),
    unchanged: countOf("unchanged"),
    errors: countOf("error"),
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <button type="button" className="block text-left">
            <div
              className="relative flex h-36 flex-col rounded-xl border-2 bg-card p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
              style={{ borderColor: accentColor }}
            >
              <div className="flex flex-1 items-center justify-center" style={{ color: accentColor }}>
                <Icon className="size-16" aria-hidden="true" />
              </div>
              <span className="text-center text-sm font-semibold">{tileTitle}</span>
            </div>
          </button>
        }
      />
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{dialogTitle}</DialogTitle>
          <DialogDescription>{dialogDescription}</DialogDescription>
        </DialogHeader>

        <p className="rounded-md bg-muted/50 px-3 py-2 text-sm text-muted-foreground">{hint}</p>

        <div className="flex flex-col gap-2">
          <Label>{downloadTemplateLabel}</Label>
          <a href={templateUrl}>
            <Button variant="outline" type="button">
              {downloadTemplateButton}
            </Button>
          </a>
        </div>

        {canUpload ? (
          <div className="flex flex-col gap-2">
            <Label htmlFor="data-topic-import-file">{chooseFileLabel}</Label>
            <Input
              id="data-topic-import-file"
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={handleFileChange}
            />
            <Button onClick={handleUpload} disabled={isUploading || !file} className="self-start">
              {uploadButton}
            </Button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{uploadNotAllowed}</p>
        )}

        {results && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted-foreground">{importSummary(counts)}</p>
            <div className="rounded-md border [&>div]:max-h-72 [&>div]:overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {importColumnRow}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {importColumnKey}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {importColumnOutcome}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {importColumnDetail}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((row) => (
                    <TableRow key={row.row_number}>
                      <TableCell>{row.row_number}</TableCell>
                      <TableCell className="font-medium">{row.key}</TableCell>
                      <TableCell>
                        <Badge variant={OUTCOME_BADGE_VARIANT[row.outcome]}>{importOutcomeLabel(row.outcome)}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{row.detail}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        <DialogFooter className="justify-start sm:justify-start">
          <div className="flex flex-col gap-2">
            <Label>{exportLabel}</Label>
            <a href={exportUrl}>
              <Button variant="outline" type="button">
                {exportButton}
              </Button>
            </a>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
