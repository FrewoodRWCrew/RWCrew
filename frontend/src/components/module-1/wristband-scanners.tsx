"use client";

// The Scans module's wristband "Scanners" screen: the wristband company's
// scanners, registered automatically by their first message, each with our
// own label such as "Balie 1" (saved when leaving the field). Every counter
// then picks its scanner on its own desk screen.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, listWristbandScanners, saveWristbandScannerLabel } from "@/lib/api";
import { formatDateTimeNl } from "@/lib/date-time";
import type { WristbandScanner } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

export function WristbandScanners({ canEdit }: { canEdit: boolean }) {
  const t = useTranslations("wristband.scanners");
  const scanners = useKeyedLoad<WristbandScanner[]>("wristband-scanners", listWristbandScanners);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>
      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("deviceId")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("deviceName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("label")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("lastSeen")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(scanners.data ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground">
                  {t("noScanners")}
                </TableCell>
              </TableRow>
            )}
            {(scanners.data ?? []).map((scanner) => (
              <TableRow key={scanner.id}>
                <TableCell className="font-mono text-sm">{scanner.device_id}</TableCell>
                <TableCell>{scanner.device_name}</TableCell>
                <TableCell>
                  <ScannerLabel scanner={scanner} canEdit={canEdit} onSaved={scanners.reload} />
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {scanner.last_seen_at ? formatDateTimeNl(scanner.last_seen_at) : ""}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

/** A scanner's own label, saved when leaving the field. */
function ScannerLabel({ scanner, canEdit, onSaved }: { scanner: WristbandScanner; canEdit: boolean; onSaved: () => void }) {
  const t = useTranslations("wristband.scanners");
  const [value, setValue] = useState(scanner.label ?? "");

  async function save() {
    if (value.trim() === (scanner.label ?? "")) return;
    try {
      await saveWristbandScannerLabel(scanner.id, value.trim() || null);
      toast.success(t("saved"));
      onSaved();
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveFailed"));
    }
  }

  return (
    <Input
      className="w-48"
      placeholder={t("labelPlaceholder")}
      value={value}
      disabled={!canEdit}
      onChange={(event) => setValue(event.target.value)}
      onBlur={() => void save()}
    />
  );
}
