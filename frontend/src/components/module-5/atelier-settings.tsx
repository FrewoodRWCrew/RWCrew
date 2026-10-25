"use client";

// Atelier's "Instellingen" screen (block 5):
//   - the global switch "Polsband verplicht bij Ophalen";
//   - the webhook address the wristband company posts its scans to, and
//     whether its token is configured on this server (ATELIER_WEBHOOK_TOKEN);
//   - the scanners that sent scans (registered automatically by their first
//     message), each with our own label such as "Balie 1";
//   - the log of every received message (also refused and ignored ones),
//     with the message as received, to check what really arrives.

import { useState, useSyncExternalStore } from "react";
import { Eye, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ApiError,
  getAtelierSettings,
  listAtelierScanLog,
  listAtelierScanners,
  saveAtelierScannerLabel,
  saveAtelierSettings,
} from "@/lib/api";
import { formatDateTimeNl } from "@/lib/date-time";
import type { AtelierScan, AtelierScanner, AtelierSettings as Settings } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

/** The colour of a scan status in the log. */
export const SCAN_STATUS_VARIANT: Record<AtelierScan["status"], "default" | "secondary" | "outline" | "destructive"> = {
  new: "default",
  used: "secondary",
  dismissed: "outline",
  ignored: "outline",
  refused: "destructive",
};

interface AtelierSettingsScreenProps {
  canEdit: boolean;
}

export function AtelierSettingsScreen({ canEdit }: AtelierSettingsScreenProps) {
  const t = useTranslations("atelier.settings");
  const settings = useKeyedLoad<Settings>("atelier-settings", getAtelierSettings);
  const scanners = useKeyedLoad<AtelierScanner[]>("atelier-scanners", listAtelierScanners);
  const log = useKeyedLoad<AtelierScan[]>("atelier-scan-log", listAtelierScanLog);
  const [isSaving, setIsSaving] = useState(false);

  async function toggleRequired(value: boolean) {
    setIsSaving(true);
    try {
      settings.setData(await saveAtelierSettings(value));
      toast.success(t("saved"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveFailed"));
    } finally {
      setIsSaving(false);
    }
  }

  // The webhook's full address on this server (the origin is only known in the browser).
  const origin = useSyncExternalStore(noSubscribe, () => window.location.origin, () => "");
  const webhookUrl = settings.data ? `${origin}${settings.data.webhook_path}` : "";

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      {settings.data && (
        <Card>
          <CardContent className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <Checkbox
                id="atelier-wristband-required"
                checked={settings.data.wristband_required}
                disabled={!canEdit || isSaving}
                onCheckedChange={(checked) => void toggleRequired(checked === true)}
              />
              <label htmlFor="atelier-wristband-required" className="font-medium">
                {t("wristbandRequired")}
              </label>
            </div>
            <p className="text-sm text-muted-foreground">{t("wristbandRequiredHelp")}</p>
            <div className="flex flex-col gap-1 border-t pt-4">
              <p className="font-medium">{t("webhookTitle")}</p>
              <code className="w-fit rounded bg-muted px-2 py-1 text-sm">POST {webhookUrl}</code>
              <p className={settings.data.webhook_token_configured ? "text-sm text-muted-foreground" : "text-sm text-destructive"}>
                {settings.data.webhook_token_configured ? t("tokenConfigured") : t("tokenMissing")}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      <section className="flex flex-col gap-2">
        <h2 className="text-lg font-semibold">{t("scannersTitle")}</h2>
        <p className="text-sm text-muted-foreground">{t("scannersHelp")}</p>
        <div className="rounded-md border [&>div]:max-h-[40vh] [&>div]:overflow-y-auto">
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
      </section>

      <section className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">{t("logTitle")}</h2>
          <Button variant="outline" size="sm" onClick={log.reload}>
            <RefreshCw className="size-4" />
            {t("refresh")}
          </Button>
        </div>
        <ScanLogTable scans={log.data ?? []} isLoading={log.isLoading} />
      </section>
    </div>
  );
}

/** A scanner's own label, saved when leaving the field. */
function ScannerLabel({ scanner, canEdit, onSaved }: { scanner: AtelierScanner; canEdit: boolean; onSaved: () => void }) {
  const t = useTranslations("atelier.settings");
  const [value, setValue] = useState(scanner.label ?? "");

  async function save() {
    if (value.trim() === (scanner.label ?? "")) return;
    try {
      await saveAtelierScannerLabel(scanner.id, value.trim() || null);
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

/** The received messages, newest first, each with its raw message in a dialog. */
export function ScanLogTable({ scans, isLoading }: { scans: AtelierScan[]; isLoading: boolean }) {
  const t = useTranslations("atelier.settings");
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

/** useSyncExternalStore's subscribe for a value that never changes. */
function noSubscribe() {
  return () => undefined;
}

/** A raw message, indented when it is JSON. */
function prettyJson(raw: string) {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}
