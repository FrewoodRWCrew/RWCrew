"use client";

// The super admin's "Login History" screen: a read-only, paginated,
// date-filterable table of every login attempt (successful or not) —
// see backend/app/landing/admin.py's GET /api/admin/login-history for
// the matching API endpoint.

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { listLoginHistory } from "@/lib/api";
import type { LoginHistoryPage } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface LoginHistoryTableProps {
  initialData: LoginHistoryPage;
  pageSize: number;
}

export function LoginHistoryTable({ initialData, pageSize }: LoginHistoryTableProps) {
  const t = useTranslations("admin.loginHistory");
  const [data, setData] = useState(initialData);
  const [page, setPage] = useState(1);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  // Skip the very first render, since initialData already reflects
  // page 1 with no filters — fetch again only once page/filters change.
  const hasMounted = useRef(false);

  useEffect(() => {
    if (!hasMounted.current) {
      hasMounted.current = true;
      return;
    }

    let isCancelled = false;
    setIsLoading(true);

    listLoginHistory({
      page,
      pageSize,
      dateFrom: dateFrom ? `${dateFrom}T00:00:00` : undefined,
      dateTo: dateTo ? `${dateTo}T23:59:59` : undefined,
    })
      .then((result) => {
        if (!isCancelled) setData(result);
      })
      .catch(() => {
        if (!isCancelled) toast.error(t("loadFailed"));
      })
      .finally(() => {
        if (!isCancelled) setIsLoading(false);
      });

    return () => {
      isCancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, dateFrom, dateTo]);

  function handleFilterChange(setter: (value: string) => void, value: string) {
    setter(value);
    setPage(1);
  }

  function handleClearFilters() {
    setDateFrom("");
    setDateTo("");
    setPage(1);
  }

  const totalPages = Math.max(Math.ceil(data.total / pageSize), 1);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-2">
          <Label htmlFor="login-history-date-from">{t("dateFromLabel")}</Label>
          <Input
            id="login-history-date-from"
            type="date"
            value={dateFrom}
            onChange={(event) => handleFilterChange(setDateFrom, event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="login-history-date-to">{t("dateToLabel")}</Label>
          <Input
            id="login-history-date-to"
            type="date"
            value={dateTo}
            onChange={(event) => handleFilterChange(setDateTo, event.target.value)}
          />
        </div>
        {(dateFrom || dateTo) && (
          <Button variant="ghost" onClick={handleClearFilters}>
            {t("clearFilters")}
          </Button>
        )}
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTimestamp")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnUser")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnStatus")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnSource")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnIpAddress")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.length === 0 && !isLoading && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  {t("empty")}
                </TableCell>
              </TableRow>
            )}
            {data.items.map((entry) => (
              <TableRow key={entry.id}>
                <TableCell>{new Date(entry.created_at).toLocaleString()}</TableCell>
                <TableCell>
                  <div className="flex flex-col">
                    <span className="font-medium">{entry.display_name ?? entry.email_attempted}</span>
                    {entry.display_name && (
                      <span className="text-xs text-muted-foreground">{entry.email_attempted}</span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <Badge variant={entry.success ? "secondary" : "destructive"}>
                    {entry.success ? t("statusSuccess") : t("statusFailed")}
                  </Badge>
                </TableCell>
                {/* Web app vs. smartphone app; "—" for attempts from before this was tracked. */}
                <TableCell>
                  {entry.source ? (
                    <Badge variant="outline">{entry.source === "mobile" ? t("sourceMobile") : t("sourceWeb")}</Badge>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground">{entry.ip_address ?? "—"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-end gap-3">
        <span className="text-sm text-muted-foreground">{t("pageOf", { page, totalPages })}</span>
        <Button variant="outline" size="sm" disabled={page <= 1 || isLoading} onClick={() => setPage((current) => current - 1)}>
          {t("previous")}
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= totalPages || isLoading}
          onClick={() => setPage((current) => current + 1)}
        >
          {t("next")}
        </Button>
      </div>
    </div>
  );
}
