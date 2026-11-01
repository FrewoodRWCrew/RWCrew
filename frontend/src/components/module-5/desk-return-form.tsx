"use client";

// Atelier's Terugbrengen: find the person, tick what came back and optionally
// note per piece what was wrong with it (return status, only a remark). Used
// by the desk ("Uitgifte & inname") and in Openstaand's Inname dialog.

import { useEffect, useState } from "react";
import { PackageMinus, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  cancelAtelierHandout,
  listAtelierDeskReturnStatuses,
  listAtelierPersonOpenHandouts,
  returnAtelierPersonLines,
  searchAtelierDeskPersons,
} from "@/lib/api";
import { formatDateNl, formatDateTimeNl } from "@/lib/date-time";
import { maskEmail } from "@/lib/mask-email";
import type { AtelierDeskPerson, AtelierHandout, AtelierReturnStatus, WristbandScan } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";
import { atelierDeskErrorMessage } from "@/components/module-5/desk-common";

// The dropdown's "nothing wrong" choice (Base UI's Select needs a non-empty value).
const NO_STATUS = "none";

/** What the form needs of the person it opens with. */
type ReturnPerson = Pick<AtelierDeskPerson, "id" | "name" | "email" | "bracelet_number">;

interface ReturnFormProps {
  canCancel: boolean;
  /** Opens with this person chosen (from Ophalen's "Eerst terugbrengen", a scan or Openstaand). */
  initialPerson: ReturnPerson | null;
  /** Openstaand's dialog: only this person, so no "Andere persoon". */
  fixedPerson?: boolean;
  /** A scanned person not found: the search starts with this text. */
  initialQuery: string;
  /** The wristband scan this return starts from (marked used by the first booking). */
  scan: WristbandScan | null;
  onDone: () => void;
}

/** Terugbrengen: find the person, tick what came back. */
export function ReturnForm({ canCancel, initialPerson, fixedPerson = false, initialQuery, scan, onDone }: ReturnFormProps) {
  const t = useTranslations("atelier.desk");
  const tStock = useTranslations("atelier.stock");
  const tFit = useTranslations("atelier.fits");
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<AtelierDeskPerson[]>([]);
  const [person, setPerson] = useState<ReturnPerson | null>(initialPerson);
  // The chosen person's open pick-ups.
  const openHandouts = useKeyedLoad<AtelierHandout[]>(person ? String(person.id) : null, () =>
    listAtelierPersonOpenHandouts(person!.id),
  );
  const handouts = openHandouts.data ?? [];
  // Every piece starts ticked; this keeps the ones the desk unticked.
  const [unticked, setUnticked] = useState<number[]>([]);
  const openLines = handouts.flatMap((handout) => handout.lines.filter((line) => !line.returned_at));
  const ticked = openLines.filter((line) => !unticked.includes(line.id)).map((line) => line.id);
  const [isBusy, setIsBusy] = useState(false);
  // What's wrong with a piece, per hand-out line (no entry = no remark).
  const statuses = useKeyedLoad<AtelierReturnStatus[]>("desk-return-statuses", listAtelierDeskReturnStatuses);
  const [lineStatuses, setLineStatuses] = useState<Record<number, number>>({});

  // Search shortly after typing stops (at least 2 characters); only people with pieces out.
  useEffect(() => {
    const value = query.trim();
    if (value.length < 2) return;
    const timer = window.setTimeout(() => {
      searchAtelierDeskPersons(value, true)
        .then(setResults)
        .catch(() => setResults([]));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [query]);

  function choose(item: AtelierDeskPerson) {
    setPerson(item);
    setUnticked([]);
    setLineStatuses({});
  }

  // Unticking a piece also drops its return status.
  function toggleLine(lineId: number, isTicked: boolean) {
    setUnticked((current) => (isTicked ? current.filter((id) => id !== lineId) : [...current, lineId]));
    if (!isTicked) setLineStatus(lineId, NO_STATUS);
  }

  function setLineStatus(lineId: number, value: string | null) {
    setLineStatuses((current) => {
      const next = { ...current };
      if (value && value !== NO_STATUS) next[lineId] = Number(value);
      else delete next[lineId];
      return next;
    });
  }

  async function handleReturn() {
    // Pieces left unticked stay with the person: confirm that first.
    const staying = openLines.filter((line) => unticked.includes(line.id));
    if (
      staying.length > 0 &&
      !window.confirm(
        t("stayingConfirm", { pieces: staying.map((line) => `${line.article_name} ${line.size_name}`).join(", ") }),
      )
    ) {
      return;
    }
    setIsBusy(true);
    try {
      // Every ticked piece in one call (whatever pick-up it came from), so the
      // person gets one "Inname" mail; the scan (if any) is marked used.
      if (person && ticked.length > 0) {
        const chosenStatuses = Object.fromEntries(
          ticked.filter((lineId) => lineId in lineStatuses).map((lineId) => [lineId, lineStatuses[lineId]]),
        );
        await returnAtelierPersonLines(person.id, ticked, scan?.id ?? null, chosenStatuses);
      }
      toast.success(t("returned", { name: person?.name ?? "", count: ticked.length }));
      onDone();
    } catch (error) {
      toast.error(atelierDeskErrorMessage(t, tStock, error));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCancel(handout: AtelierHandout) {
    if (!window.confirm(t("cancelConfirm"))) return;
    setIsBusy(true);
    try {
      await cancelAtelierHandout(handout.id);
      toast.success(t("cancelled"));
      onDone();
    } catch (error) {
      toast.error(atelierDeskErrorMessage(t, tStock, error));
    } finally {
      setIsBusy(false);
    }
  }

  if (person === null) {
    return (
      <div className="flex max-w-2xl flex-col gap-3">
        <Label htmlFor="atelier-desk-search">{t("searchLabel")}</Label>
        <div className="relative">
          <Search className="absolute top-2.5 left-3 size-4 text-muted-foreground" />
          <Input
            id="atelier-desk-search"
            autoFocus
            autoComplete="off"
            className="pl-9"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </div>
        {query.trim().length >= 2 && results.length === 0 && (
          <p className="text-sm text-muted-foreground">{t("noOpenPerson")}</p>
        )}
        {results.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => choose(item)}
            className="flex items-center justify-between rounded-md border px-4 py-3 text-left hover:bg-muted"
          >
            <span>
              <span className="font-medium">{item.name}</span>
              <span className="text-sm text-muted-foreground">
                {item.email && ` · ${maskEmail(item.email)}`}
                {item.bracelet_number && ` · ${t("braceletShort", { number: item.bracelet_number })}`}
              </span>
            </span>
            <span className="text-sm text-muted-foreground">{t("piecesOut", { count: item.open_lines.length })}</span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <p>
        <span className="text-lg font-semibold">{person.name}</span>
        {person.email && <span className="text-muted-foreground"> · {maskEmail(person.email)}</span>}
        {person.bracelet_number && (
          <span className="text-muted-foreground"> · {t("braceletShort", { number: person.bracelet_number })}</span>
        )}
      </p>
      {openHandouts.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {!openHandouts.isLoading && handouts.length === 0 && <p className="text-sm text-muted-foreground">{t("nothingOut")}</p>}
      {handouts.map((handout) => {
        const nothingReturned = handout.lines.every((line) => !line.returned_at);
        return (
          <Card key={handout.id}>
            <CardContent className="flex flex-col gap-3">
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                <span>
                  {handout.team_name} · {handout.festival_name} · {formatDateNl(handout.day)} ·{" "}
                  {t("handedOutAt", { moment: formatDateTimeNl(handout.created_at) })}
                </span>
                {canCancel && nothingReturned && (
                  <Button variant="ghost" size="sm" className="text-destructive" disabled={isBusy} onClick={() => void handleCancel(handout)}>
                    {t("cancelHandout")}
                  </Button>
                )}
              </div>
              {handout.lines
                .filter((line) => !line.returned_at)
                .map((line) => (
                  <div key={line.id} className="flex flex-wrap items-center justify-between gap-3">
                    <label className="flex items-center gap-3 text-base">
                      <Checkbox
                        checked={ticked.includes(line.id)}
                        onCheckedChange={(checked) => toggleLine(line.id, checked === true)}
                      />
                      {line.article_name} · {line.size_name} · {tFit(line.fit)}
                    </label>
                    {/* Only a piece that comes back can have a return status. */}
                    {ticked.includes(line.id) && (statuses.data ?? []).length > 0 && (
                      <SearchableSelect
                        value={String(lineStatuses[line.id] ?? NO_STATUS)}
                        onValueChange={(value) => setLineStatus(line.id, value)}
                        aria-label={t("returnStatusLabel", { article: line.article_name })}
                        className="w-56"
                        renderValue={(value: string | null) =>
                          (statuses.data ?? []).find((status) => String(status.id) === value)?.name ?? t("noReturnStatus")
                        }
                        options={[
                          { value: NO_STATUS, label: t("noReturnStatus") },
                          ...(statuses.data ?? []).map((status) => ({ value: String(status.id), label: status.name })),
                        ]}
                      />
                    )}
                  </div>
                ))}
            </CardContent>
          </Card>
        );
      })}
      <div className="flex gap-3">
        <Button size="lg" className="bg-sky-600 text-lg hover:bg-sky-700" disabled={ticked.length === 0 || isBusy} onClick={() => void handleReturn()}>
          <PackageMinus className="size-5" />
          {t("takeBack", { count: ticked.length })}
        </Button>
        {!fixedPerson && (
          <Button variant="outline" size="lg" onClick={() => setPerson(null)}>
            {t("otherPerson")}
          </Button>
        )}
      </div>
    </div>
  );
}
