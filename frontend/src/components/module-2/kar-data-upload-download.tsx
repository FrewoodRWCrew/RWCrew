"use client";

// KarTracker's "Data Upload/Download" screen: a tile grid, one tile per
// master-data topic's bulk import/export tools — same visual idiom as the
// app's own main landing page (see components/landing/module-tile.tsx),
// but each tile opens a dialog instead of navigating, since there's
// nowhere further to go. Phase 1 shipped a single "Karren" tile; phase 2
// added a second, "KarStatussen" — both now built on the same
// DataTopicTile presentational component below, so a third future tile
// doesn't have to re-copy this dialog's ~150 lines again.
//
// Each tile's dialog combines template download / bulk upload / export,
// mirroring TagScan's own import dialog
// (components/module-1/tag-import-dialog.tsx) — except a duplicate key
// (kar_nummer / status name) is reported as an error, never upserted (see
// kar_import.py / kar_status_import.py on the backend for why), so there's
// no "updated" outcome here.

import { useState } from "react";
import { FileSpreadsheet, ListChecks, MapPin, Route, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { API_BASE_URL } from "@/lib/config";
import { ApiError, importAfleverlocaties, importDistributiepunten, importKarStatuses, importKarren, importZones } from "@/lib/api";
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
 * topic's own wire type (KarImportRowResult/KarStatusImportRowResult) it
 * came from — each wrapper below maps its own "key" field (kar_nummer/
 * name) into this before handing it to the shared dialog.
 */
interface ImportRowResult {
  row_number: number;
  key: string | null;
  outcome: "created" | "error";
  detail: string | null;
}

const OUTCOME_BADGE_VARIANT: Record<ImportRowResult["outcome"], "default" | "destructive"> = {
  created: "default",
  error: "destructive",
};

interface KarDataUploadDownloadProps {
  /** Whether the current user has "create" (not just "view") permission on
   * the "kartracker.dataupload" screen — gates the upload control on both
   * tiles below, since view-only access is enough to reach this screen and
   * use its template/export links, but not enough to actually import.
   */
  canUpload: boolean;
}

export function KarDataUploadDownload({ canUpload }: KarDataUploadDownloadProps) {
  const t = useTranslations("karTracker.dataUploadDownload");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="grid max-w-3xl grid-cols-3 gap-4">
        <KarDataTile canUpload={canUpload} />
        <KarStatusDataTile canUpload={canUpload} />
        <DistributiepuntDataTile canUpload={canUpload} />
        <ZoneDataTile canUpload={canUpload} />
        <AfleverlocatieDataTile canUpload={canUpload} />
      </div>
    </div>
  );
}

function KarDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("karTracker.dataUploadDownload");

  return (
    <DataTopicTile
      icon={FileSpreadsheet}
      tileTitle={t("karrenTileTitle")}
      dialogTitle={t("karrenTileTitle")}
      dialogDescription={t("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-2/kar-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-2/karren/export`}
      downloadTemplateLabel={t("downloadTemplateLabel")}
      downloadTemplateButton={t("downloadTemplateButton")}
      canUpload={canUpload}
      uploadNotAllowed={t("uploadNotAllowed")}
      chooseFileLabel={t("chooseFileLabel")}
      uploadButton={t("uploadButton")}
      importFailed={t("importFailed")}
      importSummary={(created, errors) => t("importSummary", { created, errors })}
      importColumnRow={t("importColumnRow")}
      importColumnKey={t("importColumnKarNummer")}
      importColumnOutcome={t("importColumnOutcome")}
      importColumnDetail={t("importColumnDetail")}
      importOutcomeLabel={(outcome) => t(`importOutcome.${outcome}`)}
      exportLabel={t("exportLabel")}
      exportButton={t("exportButton")}
      onUpload={async (file) => {
        const response = await importKarren(file);
        return response.results.map((row) => ({ ...row, key: row.kar_nummer }));
      }}
    />
  );
}

function KarStatusDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("karTracker.dataUploadDownload");
  const tStatuses = useTranslations("karTracker.dataUploadDownload.karStatuses");

  return (
    <DataTopicTile
      icon={ListChecks}
      tileTitle={tStatuses("tileTitle")}
      dialogTitle={tStatuses("tileTitle")}
      dialogDescription={tStatuses("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-2/kar-status-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-2/kar-statuses/export`}
      downloadTemplateLabel={t("downloadTemplateLabel")}
      downloadTemplateButton={t("downloadTemplateButton")}
      canUpload={canUpload}
      uploadNotAllowed={t("uploadNotAllowed")}
      chooseFileLabel={t("chooseFileLabel")}
      uploadButton={t("uploadButton")}
      importFailed={t("importFailed")}
      importSummary={(created, errors) => t("importSummary", { created, errors })}
      importColumnRow={t("importColumnRow")}
      importColumnKey={tStatuses("importColumnName")}
      importColumnOutcome={t("importColumnOutcome")}
      importColumnDetail={t("importColumnDetail")}
      importOutcomeLabel={(outcome) => tStatuses(`importOutcome.${outcome}`)}
      exportLabel={t("exportLabel")}
      exportButton={tStatuses("exportButton")}
      onUpload={async (file) => {
        const response = await importKarStatuses(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function DistributiepuntDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("karTracker.dataUploadDownload");
  const tDistributiepunten = useTranslations("karTracker.dataUploadDownload.distributiepunten");

  return (
    <DataTopicTile
      icon={MapPin}
      tileTitle={tDistributiepunten("tileTitle")}
      dialogTitle={tDistributiepunten("tileTitle")}
      dialogDescription={tDistributiepunten("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-2/distributiepunt-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-2/distributiepunten/export`}
      downloadTemplateLabel={t("downloadTemplateLabel")}
      downloadTemplateButton={t("downloadTemplateButton")}
      canUpload={canUpload}
      uploadNotAllowed={t("uploadNotAllowed")}
      chooseFileLabel={t("chooseFileLabel")}
      uploadButton={t("uploadButton")}
      importFailed={t("importFailed")}
      importSummary={(created, errors) => t("importSummary", { created, errors })}
      importColumnRow={t("importColumnRow")}
      importColumnKey={tDistributiepunten("importColumnName")}
      importColumnOutcome={t("importColumnOutcome")}
      importColumnDetail={t("importColumnDetail")}
      importOutcomeLabel={(outcome) => tDistributiepunten(`importOutcome.${outcome}`)}
      exportLabel={t("exportLabel")}
      exportButton={tDistributiepunten("exportButton")}
      onUpload={async (file) => {
        const response = await importDistributiepunten(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function ZoneDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("karTracker.dataUploadDownload");
  const tZones = useTranslations("karTracker.dataUploadDownload.zones");

  return (
    <DataTopicTile
      icon={Route}
      tileTitle={tZones("tileTitle")}
      dialogTitle={tZones("tileTitle")}
      dialogDescription={tZones("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-2/zone-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-2/zones/export`}
      downloadTemplateLabel={t("downloadTemplateLabel")}
      downloadTemplateButton={t("downloadTemplateButton")}
      canUpload={canUpload}
      uploadNotAllowed={t("uploadNotAllowed")}
      chooseFileLabel={t("chooseFileLabel")}
      uploadButton={t("uploadButton")}
      importFailed={t("importFailed")}
      importSummary={(created, errors) => t("importSummary", { created, errors })}
      importColumnRow={t("importColumnRow")}
      importColumnKey={tZones("importColumnName")}
      importColumnOutcome={t("importColumnOutcome")}
      importColumnDetail={t("importColumnDetail")}
      importOutcomeLabel={(outcome) => tZones(`importOutcome.${outcome}`)}
      exportLabel={t("exportLabel")}
      exportButton={tZones("exportButton")}
      onUpload={async (file) => {
        const response = await importZones(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function AfleverlocatieDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("karTracker.dataUploadDownload");
  const tAfleverlocaties = useTranslations("karTracker.dataUploadDownload.afleverlocaties");

  return (
    <DataTopicTile
      icon={FileSpreadsheet}
      tileTitle={tAfleverlocaties("tileTitle")}
      dialogTitle={tAfleverlocaties("tileTitle")}
      dialogDescription={tAfleverlocaties("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-2/afleverlocatie-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-2/afleverlocaties/export`}
      downloadTemplateLabel={t("downloadTemplateLabel")}
      downloadTemplateButton={t("downloadTemplateButton")}
      canUpload={canUpload}
      uploadNotAllowed={t("uploadNotAllowed")}
      chooseFileLabel={t("chooseFileLabel")}
      uploadButton={t("uploadButton")}
      importFailed={t("importFailed")}
      importSummary={(created, errors) => t("importSummary", { created, errors })}
      importColumnRow={t("importColumnRow")}
      importColumnKey={tAfleverlocaties("importColumnName")}
      importColumnOutcome={t("importColumnOutcome")}
      importColumnDetail={t("importColumnDetail")}
      importOutcomeLabel={(outcome) => tAfleverlocaties(`importOutcome.${outcome}`)}
      exportLabel={t("exportLabel")}
      exportButton={tAfleverlocaties("exportButton")}
      onUpload={async (file) => {
        const response = await importAfleverlocaties(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

interface DataTopicTileProps {
  icon: LucideIcon;
  tileTitle: string;
  dialogTitle: string;
  dialogDescription: string;
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
  importSummary: (created: number, errors: number) => string;
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
 * One tile on the Data Upload/Download grid: a button styled as an
 * outlined card (this module's own accent colour as the border, not a
 * solid fill — a deliberately lighter look than the landing page's own
 * fully-coloured ModuleTile) that opens a dialog with that topic's
 * template download / bulk upload / export tools.
 */
function DataTopicTile({
  icon: Icon,
  tileTitle,
  dialogTitle,
  dialogDescription,
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
  const { accentColorToken } = getModuleTheme("module-2");
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

  const createdCount = results?.filter((row) => row.outcome === "created").length ?? 0;
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
            <p className="text-sm text-muted-foreground">{importSummary(createdCount, errorCount)}</p>
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
