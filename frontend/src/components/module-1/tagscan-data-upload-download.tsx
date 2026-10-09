"use client";

// TagScan's "Data Upload/Download" screen: a tile grid, one tile per TagScan
// table (Tags and Scanners), each opening a dialog with that table's
// template download / bulk upload / export tools. Same look and flow as
// MasterData's components/module-9/masterdata-data-upload-download.tsx
// (duplicated here rather than shared, matching the convention that each
// module's UI stays self-contained under its own components/module-{N}/
// folder). Unlike MasterData, both TagScan imports upsert: a row naming an
// existing EPC / scanner updates it, so the outcome can also be "updated".

import { useState } from "react";
import { ScanLine, Tag, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { API_BASE_URL } from "@/lib/config";
import { ApiError, importRfidTags, importScanners } from "@/lib/api";
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
 * table it came from — each tile maps its own key field (epc_uid /
 * scanner) into `key` before handing it to the shared dialog. */
interface ImportRowResult {
  row_number: number;
  key: string | null;
  outcome: "created" | "updated" | "error";
  detail: string | null;
}

const OUTCOME_BADGE_VARIANT: Record<ImportRowResult["outcome"], "default" | "secondary" | "destructive"> = {
  created: "default",
  updated: "secondary",
  error: "destructive",
};

interface TagscanDataUploadDownloadProps {
  /** Whether the current user has "create" (not just "view") on the
   * "tagscan.dataupload" screen — view is enough for the template and
   * export links, but uploading needs create. */
  canUpload: boolean;
}

export function TagscanDataUploadDownload({ canUpload }: TagscanDataUploadDownloadProps) {
  const t = useTranslations("tagscan.dataUploadDownload");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="grid max-w-4xl grid-cols-3 gap-4">
        <DataTopicTile
          icon={Tag}
          table="tags"
          templateUrl={`${API_BASE_URL}/api/modules/module-1/tag-import/template`}
          exportUrl={`${API_BASE_URL}/api/modules/module-1/tags/export`}
          canUpload={canUpload}
          onUpload={async (file) => {
            const response = await importRfidTags(file);
            return response.results.map((row) => ({ ...row, key: row.epc_uid }));
          }}
        />
        <DataTopicTile
          icon={ScanLine}
          table="scanners"
          templateUrl={`${API_BASE_URL}/api/modules/module-1/scanner-import/template`}
          exportUrl={`${API_BASE_URL}/api/modules/module-1/scanners/export`}
          canUpload={canUpload}
          onUpload={async (file) => {
            const response = await importScanners(file);
            return response.results.map((row) => ({ ...row, key: row.scanner }));
          }}
        />
      </div>
    </div>
  );
}

interface DataTopicTileProps {
  icon: LucideIcon;
  /** The tile's own translation group under tagscan.dataUploadDownload. */
  table: "tags" | "scanners";
  templateUrl: string;
  exportUrl: string;
  canUpload: boolean;
  onUpload: (file: File) => Promise<ImportRowResult[]>;
}

/**
 * One tile on the grid: a button styled as an outlined card (this module's
 * accent colour as the border) that opens a dialog with that table's
 * template download / bulk upload / export tools.
 */
function DataTopicTile({ icon: Icon, table, templateUrl, exportUrl, canUpload, onUpload }: DataTopicTileProps) {
  const t = useTranslations("tagscan.dataUploadDownload");
  const tTable = useTranslations(`tagscan.dataUploadDownload.${table}`);
  const { accentColorToken } = getModuleTheme("module-1");
  const accentColor = `var(--color-${accentColorToken})`;

  const [isOpen, setIsOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [results, setResults] = useState<ImportRowResult[] | null>(null);
  const fileInputId = `tagscan-${table}-import-file`;

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
    // A different file clears the results: they describe the previous file.
    setFile(event.target.files?.[0] ?? null);
    setResults(null);
  }

  async function handleUpload() {
    if (!file) return;

    // Clear the previous results right away, so a slow or failed request
    // never leaves stale rows on screen that look like this file's outcome.
    setResults(null);
    setIsUploading(true);
    try {
      setResults(await onUpload(file));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("importFailed");
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  // Counts for the summary line above the results table.
  const createdCount = results?.filter((row) => row.outcome === "created").length ?? 0;
  const updatedCount = results?.filter((row) => row.outcome === "updated").length ?? 0;
  const errorCount = results?.filter((row) => row.outcome === "error").length ?? 0;

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
              <span className="text-center text-sm font-semibold">{tTable("tileTitle")}</span>
            </div>
          </button>
        }
      />
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{tTable("tileTitle")}</DialogTitle>
          <DialogDescription>{tTable("dialogDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label>{t("downloadTemplateLabel")}</Label>
          <a href={templateUrl}>
            <Button variant="outline" type="button">
              {t("downloadTemplateButton")}
            </Button>
          </a>
        </div>

        {canUpload ? (
          <div className="flex flex-col gap-2">
            <Label htmlFor={fileInputId}>{t("chooseFileLabel")}</Label>
            <Input
              id={fileInputId}
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={handleFileChange}
            />
            <Button onClick={handleUpload} disabled={isUploading || !file} className="self-start">
              {t("uploadButton")}
            </Button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{t("uploadNotAllowed")}</p>
        )}

        {results && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted-foreground">
              {t("importSummary", { created: createdCount, updated: updatedCount, errors: errorCount })}
            </p>
            <div className="rounded-md border [&>div]:max-h-72 [&>div]:overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("importColumnRow")}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {tTable("importColumnKey")}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("importColumnOutcome")}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("importColumnDetail")}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((row) => (
                    <TableRow key={row.row_number}>
                      <TableCell>{row.row_number}</TableCell>
                      <TableCell className="font-medium">{row.key}</TableCell>
                      <TableCell>
                        <Badge variant={OUTCOME_BADGE_VARIANT[row.outcome]}>{t(`importOutcome.${row.outcome}`)}</Badge>
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
            <Label>{t("exportLabel")}</Label>
            <a href={exportUrl}>
              <Button variant="outline" type="button">
                {tTable("exportButton")}
              </Button>
            </a>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
