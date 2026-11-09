"use client";

// StockMaster's "Historiek > Tag-historiek" screen: the trace of one product
// piece by its RFID tag (EPC). Type or paste the EPC (or open it with ?epc=):
// the tag as Scans > Tagbeheer knows it now (product, status, last known
// place, last read), and every booking made on the RWCrew Pi that moved it,
// newest first, from which place to which. Read-only.
//
// Only Pi bookings move tags: a web booking moves quantities without knowing
// which tags, so the place shown is "where the Pi last saw it".

import { useState, type FormEvent } from "react";
import { History, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/navigation";
import { useSearchParams } from "next/navigation";
import { getStockMasterTagHistory } from "@/lib/api";
import { formatDateTimeNl } from "@/lib/date-time";
import type { StockMasterTagHistory, StockMasterTagPlace } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

// The table's columns, in order.
const COLUMNS = ["when", "booking", "from", "to", "bookedBy"] as const;

// The colour of a place.
const PLACE_CLASS: Record<StockMasterTagPlace | "unknown", string> = {
  free: "bg-green-100 text-green-800 dark:bg-green-950 dark:text-green-200",
  kar: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-200",
  out: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-200",
  written_off: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
  unknown: "bg-muted text-muted-foreground",
};

export function StockMasterTagHistory() {
  const t = useTranslations("stockMaster.tagHistory");
  const tDocTypes = useTranslations("stockMaster.docTypes");
  const router = useRouter();
  const pathname = usePathname();
  // The EPC looked up travels in the URL (?epc=), so a link opens it straight away.
  const epc = useSearchParams().get("epc")?.trim() ?? "";
  const [typed, setTyped] = useState(epc);
  const history = useKeyedLoad<StockMasterTagHistory>(epc || null, () => getStockMasterTagHistory(epc));

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
          <Label htmlFor="stockmaster-tag-history-epc">{t("epcLabel")}</Label>
          <Input
            id="stockmaster-tag-history-epc"
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
              <dl className="mt-2 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
                <div>
                  <dt className="text-muted-foreground">{t("product")}</dt>
                  <dd className="font-medium">{data.product_name ?? t("noProduct")}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t("status")}</dt>
                  <dd className="font-medium">{data.status}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">{t("place")}</dt>
                  <dd className="flex flex-col gap-1">
                    <PlaceBadge place={data.place} kar={data.place_kar_nummer} />
                    {data.place_at && (
                      <span className="text-xs text-muted-foreground">{formatDateTimeNl(data.place_at)}</span>
                    )}
                  </dd>
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

          <p className="text-sm font-medium">{t("events", { count: data.events.length })}</p>
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
                {data.events.map((event, index) => (
                  <TableRow key={`${event.document_id}-${index}`}>
                    <TableCell>{formatDateTimeNl(event.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <span className="font-medium">
                          {tDocTypes(event.doc_type)} · <span className="font-mono text-xs">{event.doc_number}</span>
                        </span>
                        <div className="flex flex-wrap gap-1">
                          {event.status === "reversed" && <Badge variant="destructive">{t("reversed")}</Badge>}
                          {/* Only the place changed (a count with a matching quantity, a forgotten place). */}
                          {!event.counted && <Badge variant="outline">{t("placeOnly")}</Badge>}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <PlaceBadge place={event.from_place} kar={event.from_kar_nummer} />
                    </TableCell>
                    <TableCell>
                      <PlaceBadge place={event.to_place} kar={event.to_kar_nummer} />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">{event.created_by_name}</TableCell>
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

/** A tag place as a coloured pill ("Kar 12", "Vrije stock", "Onbekend"…). */
function PlaceBadge({ place, kar }: { place: StockMasterTagPlace | null; kar: string | null }) {
  const t = useTranslations("stockMaster.tagHistory.places");
  const key = place ?? "unknown";
  return (
    <span className={`w-fit rounded px-1.5 py-0.5 text-xs font-medium ${PLACE_CLASS[key]}`}>
      {t(key, { kar: kar ?? "?" })}
    </span>
  );
}
