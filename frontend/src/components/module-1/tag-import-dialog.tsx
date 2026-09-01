"use client";

// TagManagement's "Import Excel file" dialog: pick a file, upload it, then show
// the per-row outcome (created/updated/error) as a persistent, scrollable
// log inside the same dialog — it stays open until the user closes it,
// rather than a toast that disappears, since the whole point is being
// able to see exactly what happened to every row of a bulk import.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, importRfidTags } from "@/lib/api";
import type { RfidTagImportRowResult } from "@/lib/types";
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

interface TagImportDialogProps {
  trigger: React.ReactElement;
}

const OUTCOME_BADGE_VARIANT: Record<RfidTagImportRowResult["outcome"], "default" | "secondary" | "destructive"> = {
  created: "default",
  updated: "secondary",
  error: "destructive",
};

export function TagImportDialog({ trigger }: TagImportDialogProps) {
  const t = useTranslations("tagscan.tagManagement");
  const router = useRouter();

  const [isOpen, setIsOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [results, setResults] = useState<RfidTagImportRowResult[] | null>(null);

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
      const response = await importRfidTags(file);
      setResults(response.results);
      // Any created/updated rows need to show up in the table below.
      router.refresh();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("importFailed");
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  const createdCount = results?.filter((row) => row.outcome === "created").length ?? 0;
  const updatedCount = results?.filter((row) => row.outcome === "updated").length ?? 0;
  const errorCount = results?.filter((row) => row.outcome === "error").length ?? 0;

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger} />
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("importCsvTitle")}</DialogTitle>
          <DialogDescription>{t("importCsvDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor="tag-import-file">{t("chooseFileLabel")}</Label>
          <Input
            id="tag-import-file"
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </div>

        {results && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted-foreground">
              {t("importSummary", { created: createdCount, updated: updatedCount, errors: errorCount })}
            </p>
            <div className="max-h-72 overflow-y-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="font-bold underline">{t("importColumnRow")}</TableHead>
                    <TableHead className="font-bold underline">{t("importColumnEpcUid")}</TableHead>
                    <TableHead className="font-bold underline">{t("importColumnOutcome")}</TableHead>
                    <TableHead className="font-bold underline">{t("importColumnDetail")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((row) => (
                    <TableRow key={row.row_number}>
                      <TableCell>{row.row_number}</TableCell>
                      <TableCell className="font-medium">{row.epc_uid}</TableCell>
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

        <DialogFooter>
          <Button onClick={handleUpload} disabled={isUploading || !file}>
            {t("uploadButton")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
