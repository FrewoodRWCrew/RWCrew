"use client";

// Atelier's "Balie > Tag-historiek" screen: the trace of one clothing piece by
// its RFID tag (EPC). Type or paste the EPC (or open it from an EPC link on
// Openstaand / Retourproblemen, ?epc=): the tag as Scans > Tagbeheer knows it
// now (piece, status, last read), and every hand-out and return booked with
// that EPC, newest first, with where it was booked (website or RWCrew Pi).
// Read-only. The EPC stays on the hand-out line, so the trace survives the tag
// being deleted or linked to another piece later.

import { useState, type FormEvent } from "react";
import { History, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import { useSearchParams } from "next/navigation";
import { getAtelierTagHistory } from "@/lib/api";
import { formatDateNl, formatDateTimeNl } from "@/lib/date-time";
import type { AtelierBookingSource, AtelierTagHistory, AtelierTagHistoryEvent } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

// The table's columns, in order.
const COLUMNS = ["handedOut", "returned", "person", "team", "festival", "day", "article", "bookedBy", "returnStatus"] as const;

// The colour of an event's state.
const STATE_CLASS: Record<AtelierTagHistoryEvent["state"], string> = {
  out: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-200",
  returned: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200",
  written_off: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
  cancelled: "bg-muted text-muted-foreground",
};

const TAG_HISTORY_PATH = "/modules/module-5/desk/tag-history";

/** An EPC as a link to its Tag-historiek (used on Openstaand and Retourproblemen). */
export function EpcLink({ epc }: { epc: string | null }) {
  if (!epc) return null;
  return (
    <Link
      href={`${TAG_HISTORY_PATH}?epc=${encodeURIComponent(epc)}`}
      className="font-mono text-xs underline-offset-2 hover:underline"
    >
      {epc}
    </Link>
  );
}

export function TagHistory() {
  const t = useTranslations("atelier.tagHistory");
  const router = useRouter();
  const pathname = usePathname();
  // The EPC looked up travels in the URL (?epc=), so a link opens it straight away.
  const epc = useSearchParams().get("epc")?.trim() ?? "";
  const [typed, setTyped] = useState(epc);
  const history = useKeyedLoad<AtelierTagHistory>(epc || null, () => getAtelierTagHistory(epc));

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const value = typed.trim();
    if (value) router.replace(`${pathname}?epc=${encodeURIComponent(value)}`);
  }

  const data = history.data;
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
        <div className="flex w-full max-w-md flex-col gap-2">
          <Label htmlFor="atelier-tag-history-epc">{t("epcLabel")}</Label>
          <Input
            id="atelier-tag-history-epc"
            className="font-mono"
            placeholder={t("epcPlaceholder")}
            value={typed}
            onChange={(event) => setTyped(event.target.value)}
            autoFocus={!epc}
          />
        </div>
        <Button type="submit" disabled={!typed.trim()}>
          <Search className="size-4" />
          {t("search")}
        </Button>
      </form>

      {epc && history.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {epc && history.failed && <p className="text-sm text-destructive">{t("failed")}</p>}

      {data && (
        <>
          {/* The tag as Scans > Tagbeheer knows it now. */}
          <div className="rounded-md border p-4">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <History className="size-4" />
              <span className="font-mono">{data.epc}</span>
              {data.rfid_tag_id !== null && <Badge variant="secondary">{t("tagCard")}</Badge>}
            </div>
            {data.rfid_tag_id === null ? (
              <p className="mt-2 text-sm text-muted-foreground">{t("notFound")}</p>
            ) : (
              <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
                <div>
                  <dt className="text-muted-foreground">{t("piece")}</dt>
                  <dd className="font-medium">{data.piece ?? t("noPiece")}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t("status")}</dt>
                  <dd className="font-medium">{data.status}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t("lastRead")}</dt>
                  <dd className="font-medium">
                    {formatDateTimeNl(data.last_read_at) || "—"}
                    {data.last_reader_id && ` ${t("lastReader", { reader: data.last_reader_id })}`}
                    {data.last_location && ` ${t("at", { location: data.last_location })}`}
                  </dd>
                </div>
              </dl>
            )}
          </div>

          <div className="flex items-center justify-between">
            <p className="text-sm font-medium">{t("events", { count: data.events.length })}</p>
          </div>
          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  {COLUMNS.map((column) => (
                    <TableHead key={column} className="sticky top-0 z-20 bg-background font-bold underline">
                      {t(column)}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.events.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={COLUMNS.length} className="text-center text-muted-foreground">
                      {t("noEvents")}
                    </TableCell>
                  </TableRow>
                )}
                {data.events.map((event) => (
                  <TableRow key={event.line_id}>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <span>{formatDateTimeNl(event.handed_out_at)}</span>
                        <SourceBadge source={event.handout_source} />
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <span className={`w-fit rounded px-1.5 py-0.5 text-xs font-medium ${STATE_CLASS[event.state]}`}>
                          {t(`state.${event.state}`)}
                        </span>
                        {event.returned_at && <span>{formatDateTimeNl(event.returned_at)}</span>}
                        {event.return_source && <SourceBadge source={event.return_source} />}
                        {/* Came back with another tag than it went out with. */}
                        {event.return_epc && event.return_epc !== data.epc && (
                          <span className="font-mono text-xs text-muted-foreground">
                            {t("otherTagBack", { epc: event.return_epc })}
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-medium">{event.person_name}</TableCell>
                    <TableCell>{event.team_name}</TableCell>
                    <TableCell>{event.festival_name}</TableCell>
                    <TableCell>{formatDateNl(event.day)}</TableCell>
                    <TableCell>
                      {event.article_name} · {event.size_name}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      <div className="flex flex-col">
                        <span>{event.handed_out_by}</span>
                        {event.returned_by && <span>{event.returned_by}</span>}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{event.return_status}</TableCell>
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

/** "Website" or "Pi": where a hand-out or return was booked. */
function SourceBadge({ source }: { source: AtelierBookingSource }) {
  const t = useTranslations("atelier.tagHistory");
  return (
    <Badge variant={source === "pi" ? "default" : "outline"} className="w-fit">
      {t(`source.${source}`)}
    </Badge>
  );
}
