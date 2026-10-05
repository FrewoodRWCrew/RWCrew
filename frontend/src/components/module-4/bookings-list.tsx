"use client";

// StockMaster's "Boekingen": every booking, newest first — number, date
// (Belgian time), action, kar, lines, pieces, who booked it, and whether it
// was undone. Filters: season, action (in process order), product, kar,
// user and a date range; "?product=" and "?kar=" (from the other screens)
// open it filtered. 50 per page.

import { useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Link } from "@/i18n/navigation";
import {
  getStockMasterLookups,
  getStockMasterStock,
  listStockMasterBookings,
  listStockMasterKars,
  stockMasterBookingPdfUrl,
} from "@/lib/api";
import { formatDateTime } from "@/lib/date-time";
import type {
  Season,
  StockMasterDocumentPage,
  StockMasterKarSummary,
  StockMasterLookups,
  StockMasterProductStock,
} from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { NamedSelect } from "@/components/module-4/booking-panel";
import { ACTION_ORDER, STOCKMASTER_BASE } from "@/components/module-4/stockmaster-common";

const PAGE_SIZE = 50;
const ALL = "all";

interface BookingsListProps {
  seasons: Season[];
}

export function BookingsList({ seasons }: BookingsListProps) {
  const t = useTranslations("stockMaster");
  const tList = useTranslations("stockMaster.bookings");
  const locale = useLocale();
  const searchParams = useSearchParams();

  const [lookups, setLookups] = useState<StockMasterLookups | null>(null);
  const [products, setProducts] = useState<StockMasterProductStock[]>([]);
  const [kars, setKars] = useState<StockMasterKarSummary[]>([]);
  const [seasonId, setSeasonId] = useState<number | null>(null);
  const [docType, setDocType] = useState<string>(ALL);
  const [productId, setProductId] = useState<number | null>(() => Number(searchParams.get("product")) || null);
  const [karId, setKarId] = useState<number | null>(() => Number(searchParams.get("kar")) || null);
  const [userId, setUserId] = useState<number | null>(null);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<StockMasterDocumentPage | null>(null);

  useEffect(() => {
    getStockMasterLookups().then(setLookups).catch(() => toast.error(t("errors.loadFailed")));
    getStockMasterStock().then(setProducts).catch(() => undefined);
    listStockMasterKars(null).then(setKars).catch(() => undefined);
  }, [t]);

  useEffect(() => {
    listStockMasterBookings({
      season_id: seasonId,
      doc_type: docType === ALL ? null : docType,
      product_id: productId,
      kar_id: karId,
      user_id: userId,
      date_from: dateFrom || null,
      date_to: dateTo || null,
      offset,
      limit: PAGE_SIZE,
    })
      .then(setPage)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [seasonId, docType, productId, karId, userId, dateFrom, dateTo, offset, t]);

  // Any filter change starts again at the first page.
  function filtered<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setOffset(0);
    };
  }

  const total = page?.total ?? 0;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{tList("title")}</h1>
        <p className="text-muted-foreground">{tList("description")}</p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="w-36">
          <NamedSelect
            id="bookings-season"
            label={t("common.seasonLabel")}
            value={seasonId}
            items={seasons}
            emptyLabel={t("common.all")}
            onChange={filtered(setSeasonId)}
          />
        </div>
        <div className="flex w-44 flex-col gap-2">
          <Label htmlFor="bookings-type">{tList("action")}</Label>
          <Select value={docType} onValueChange={(value) => filtered(setDocType)(value ?? ALL)}>
            <SelectTrigger id="bookings-type" className="w-full">
              <SelectValue>{(value: string | null) => (!value || value === ALL ? t("common.all") : t(`docTypes.${value}`))}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t("common.all")}</SelectItem>
              {[...ACTION_ORDER, "reversal"].map((type) => (
                <SelectItem key={type} value={type}>
                  {t(`docTypes.${type}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-56">
          <NamedSelect
            id="bookings-product"
            label={t("common.product")}
            value={productId}
            items={products.map((product) => ({ id: product.product_id, name: product.name }))}
            emptyLabel={t("common.all")}
            onChange={filtered(setProductId)}
          />
        </div>
        <div className="w-36">
          <NamedSelect
            id="bookings-kar"
            label={t("common.kar")}
            value={karId}
            items={kars.map((kar) => ({ id: kar.kar_id, name: kar.kar_nummer }))}
            emptyLabel={t("common.all")}
            onChange={filtered(setKarId)}
          />
        </div>
        <div className="w-44">
          <NamedSelect
            id="bookings-user"
            label={tList("user")}
            value={userId}
            items={lookups?.booking_users ?? []}
            emptyLabel={t("common.all")}
            onChange={filtered(setUserId)}
          />
        </div>
        <div className="flex w-40 flex-col gap-2">
          <Label htmlFor="bookings-from">{tList("dateFrom")}</Label>
          <Input id="bookings-from" type="date" value={dateFrom} onChange={(event) => filtered(setDateFrom)(event.target.value)} />
        </div>
        <div className="flex w-40 flex-col gap-2">
          <Label htmlFor="bookings-to">{tList("dateTo")}</Label>
          <Input id="bookings-to" type="date" value={dateTo} onChange={(event) => filtered(setDateTo)(event.target.value)} />
        </div>
      </div>

      {page === null ? (
        <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
      ) : (
        <>
          <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tList("number")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tList("date")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tList("action")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.kar")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tList("details")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{tList("lines")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{tList("pieces")}</TableHead>
                  <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tList("user")}</TableHead>
                  <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                    {t("common.actions")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {page.items.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={9} className="py-8 text-center text-muted-foreground">
                      {tList("empty")}
                    </TableCell>
                  </TableRow>
                )}
                {page.items.map((document) => (
                  <TableRow key={document.id} className="group">
                    <TableCell className="font-medium">
                      <Link href={`${STOCKMASTER_BASE}/bookings/${document.id}`} className="underline">
                        {document.doc_number}
                      </Link>
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{formatDateTime(document.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap items-center gap-1">
                        <span>{t(`docTypes.${document.doc_type}`)}</span>
                        {document.status === "reversed" && <Badge variant="destructive">{tList("reversed")}</Badge>}
                      </div>
                    </TableCell>
                    <TableCell>
                      {document.from_kar_nummer ? `${document.from_kar_nummer} → ` : ""}
                      {document.kar_nummer ?? ""}
                    </TableCell>
                    <TableCell className="max-w-64 truncate text-muted-foreground">
                      {[document.reversal_of_number, document.team_name, document.festival_name, document.reason_name, document.reference]
                        .filter(Boolean)
                        .join(" · ")}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{document.line_count}</TableCell>
                    <TableCell className="text-right tabular-nums">{document.total_quantity}</TableCell>
                    <TableCell>{document.created_by_name ?? ""}</TableCell>
                    <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                      <a
                        href={stockMasterBookingPdfUrl(document.id, locale)}
                        target="_blank"
                        rel="noreferrer"
                        aria-label={tList("pdf")}
                        title={tList("pdf")}
                        className={buttonVariants({ variant: "ghost", size: "icon-sm" })}
                      >
                        <FileText />
                      </a>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{tList("range", { from: total === 0 ? 0 : offset + 1, to: Math.min(offset + PAGE_SIZE, total), total })}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                {tList("previous")}
              </Button>
              <Button variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>
                {tList("next")}
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
