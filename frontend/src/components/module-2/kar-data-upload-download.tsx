"use client";

// KarTracker's "Data Upload/Download" screen: a tile grid, one tile per
// master-data topic's bulk import/export tools — same visual idiom as the
// app's own main landing page (see components/landing/module-tile.tsx),
// but each tile opens a dialog instead of navigating, since there's
// nowhere further to go. Phase 1 ships a single "Karren" tile; phase 2
// adds more tiles to this same grid for other master-data topics, without
// touching this one.
//
// The "Karren" tile's dialog combines template download / bulk upload /
// full-database export for the fleet registry, mirroring TagScan's own
// import dialog (components/module-1/tag-import-dialog.tsx) — except a
// kar_nummer that already exists is reported as an error, never upserted
// (see kar_import.py on the backend for why), so there's no "updated"
// outcome here.

import { useState } from "react";
import { FileSpreadsheet } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { API_BASE_URL } from "@/lib/config";
import { ApiError, importKarren } from "@/lib/api";
import type { KarImportRowResult } from "@/lib/types";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";
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

const OUTCOME_BADGE_VARIANT: Record<KarImportRowResult["outcome"], "default" | "destructive"> = {
  created: "default",
  error: "destructive",
};

export function KarDataUploadDownload() {
  const t = useTranslations("karTracker.dataUploadDownload");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="grid max-w-2xl grid-cols-3 gap-4">
        <KarDataTile />
      </div>
    </div>
  );
}

function KarDataTile() {
  const t = useTranslations("karTracker.dataUploadDownload");
  const { tileClassName } = getModuleTheme("module-2");

  const [isOpen, setIsOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [results, setResults] = useState<KarImportRowResult[] | null>(null);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from a clean slate each time the dialog is opened, so a
      // previous import's results don't linger behind a new file pick.
      setFile(null);
      setResults(null);
    }
  }

  async function handleUpload() {
    if (!file) return;

    setIsUploading(true);
    try {
      const response = await importKarren(file);
      setResults(response.results);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("importFailed");
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
              className={cn(
                "relative flex h-36 flex-col rounded-xl p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg hover:brightness-110",
                tileClassName,
              )}
            >
              <div className="flex flex-1 items-center justify-center">
                <FileSpreadsheet className="size-16" aria-hidden="true" />
              </div>
              <span className="text-center text-sm font-semibold">{t("karrenTileTitle")}</span>
            </div>
          </button>
        }
      />
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("karrenTileTitle")}</DialogTitle>
          <DialogDescription>{t("dialogDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label>{t("downloadTemplateLabel")}</Label>
          <a href={`${API_BASE_URL}/api/modules/module-2/kar-import/template`}>
            <Button variant="outline" type="button">
              {t("downloadTemplateButton")}
            </Button>
          </a>
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="kar-import-file">{t("chooseFileLabel")}</Label>
          <Input
            id="kar-import-file"
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <Button onClick={handleUpload} disabled={isUploading || !file} className="self-start">
            {t("uploadButton")}
          </Button>
        </div>

        {results && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted-foreground">
              {t("importSummary", { created: createdCount, errors: errorCount })}
            </p>
            <div className="rounded-md border [&>div]:max-h-72 [&>div]:overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("importColumnRow")}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {t("importColumnKarNummer")}
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
                      <TableCell className="font-medium">{row.kar_nummer}</TableCell>
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
            <a href={`${API_BASE_URL}/api/modules/module-2/karren/export`}>
              <Button variant="outline" type="button">
                {t("exportButton")}
              </Button>
            </a>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
