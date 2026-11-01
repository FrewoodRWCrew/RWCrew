"use client";

// The received wristband messages, newest first, each with its raw message in
// a dialog. Used by the Scans module's Scans screen and by every Test-scan
// screen. A "new" scan that waits at no counter gets a note: its team has no
// reservation, so no counter shows it.

import { Eye } from "lucide-react";
import { useTranslations } from "next-intl";
import { formatDateTimeNl } from "@/lib/date-time";
import type { WristbandScan } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/** The colour of a scan status. */
export const SCAN_STATUS_VARIANT: Record<WristbandScan["status"], "default" | "secondary" | "outline" | "destructive"> = {
  new: "default",
  used: "secondary",
  dismissed: "outline",
  ignored: "outline",
  refused: "destructive",
};

export function ScanLogTable({ scans, isLoading }: { scans: WristbandScan[]; isLoading: boolean }) {
  const t = useTranslations("wristband.log");
  return (
    <div className="rounded-md border [&>div]:max-h-[50vh] [&>div]:overflow-y-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("received")}</TableHead>
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("status")}</TableHead>
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("scanner")}</TableHead>
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("person")}</TableHead>
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("wristband")}</TableHead>
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("team")}</TableHead>
            <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
              {t("message")}
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {scans.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground">
                {isLoading ? t("loading") : t("noScans")}
              </TableCell>
            </TableRow>
          )}
          {scans.map((scan) => (
            <TableRow key={scan.id} className="group">
              <TableCell className="text-sm">
                {formatDateTimeNl(scan.received_at)}
                {scan.source === "test" && (
                  <Badge variant="outline" className="ml-2 border-amber-400 text-amber-700">
                    {t("test")}
                  </Badge>
                )}
              </TableCell>
              <TableCell>
                <Badge variant={SCAN_STATUS_VARIANT[scan.status]}>{t(`statuses.${scan.status}`)}</Badge>
                {scan.status_detail && <p className="text-xs text-muted-foreground">{t(`details.${scan.status_detail}`)}</p>}
                {scan.status === "new" && scan.visible_at?.length === 0 && (
                  <p className="text-xs text-orange-700 dark:text-orange-300">{t("noReservation")}</p>
                )}
              </TableCell>
              <TableCell className="text-sm">{[scan.device_name, scan.device_id && `#${scan.device_id}`].filter(Boolean).join(" ")}</TableCell>
              <TableCell>{[scan.first_name, scan.last_name].filter(Boolean).join(" ")}</TableCell>
              <TableCell className="font-mono text-sm">{scan.wristband_number}</TableCell>
              <TableCell className="text-sm">
                {scan.team_name}
                {scan.team_name && scan.team_id === null && scan.status !== "refused" && (
                  <p className="text-xs text-orange-700 dark:text-orange-300">{t("teamNotMatched")}</p>
                )}
              </TableCell>
              <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                <div className="flex justify-end">
                  <Dialog>
                    <DialogTrigger
                      render={
                        <Button variant="ghost" size="icon" aria-label={t("message")} title={t("message")}>
                          <Eye className="size-4" />
                        </Button>
                      }
                    />
                    <DialogContent className="sm:max-w-2xl">
                      <DialogHeader>
                        <DialogTitle>{t("message")}</DialogTitle>
                      </DialogHeader>
                      <pre className="max-h-[60vh] overflow-auto rounded bg-muted p-3 text-xs whitespace-pre-wrap">
                        {prettyJson(scan.raw ?? "")}
                      </pre>
                    </DialogContent>
                  </Dialog>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

/** A raw message, indented when it is JSON. */
function prettyJson(raw: string) {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}
