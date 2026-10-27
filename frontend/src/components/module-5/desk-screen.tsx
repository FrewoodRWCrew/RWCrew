"use client";

// Atelier's "Balie > Uitgifte & inname" screen — the counter desk (block 4).
// Festival and day are chosen once at the top. Every transaction then starts
// with a choice between two big buttons, "Ophalen" (pick-up) and
// "Terugbrengen" (return) — keys 1 / 2 — which decides what kind of
// transaction it is. After booking (or "Annuleren") the screen goes back to
// that choice for the next person.
//   - Ophalen: first name, family name (together they are the person: a
//     known worker is recognised and their email, bracelet number, team and
//     pieces still out are filled in), email (optional, not unique; a filled-in
//     one is only shown masked, "Wijzig" types a new one), the
//     optional bracelet number (unique), team; then per package article a size
//     (1 piece each). Every article is optional: click the chosen size again to
//     skip it; an article with only one size in stock is pre-selected. At
//     least one article is needed. An article the person still has can't be
//     picked up again: an orange box lists what they still have, with
//     "Eerst terugbrengen" to switch straight to the return for that person.
//     "x / y persons today" turns orange above the reservation (warning only).
//     An icon on the right (level with "Gekend: …") opens the team's leads
//     (Ploegverantwoordelijken of the festival's season), only on click.
//   Wristband scans (block 5): the desk picks its scanner (remembered in this
//   browser) and polls that scanner's waiting scans every 2 seconds. On the
//   choice screen a new scan shows as a card; choosing Ophalen fills in the
//   scanned person (name, wristband number, team, size), Terugbrengen opens
//   their pieces. During a transaction a new scan only shows a small note.
//   - Terugbrengen: find the person by name, email or bracelet number, tick what came back
//     (everything is ticked by default; unticked pieces stay with the person
//     after a confirmation) and book it; a pick-up of which nothing came back
//     yet can be cancelled ("edit" right).

import { useEffect, useState } from "react";
import { Contact, PackageMinus, PackagePlus, ScanLine, Search, TriangleAlert, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ApiError,
  cancelAtelierHandout,
  dismissAtelierScan,
  getAtelierWristbandRequired,
  listAtelierDeskScanners,
  listAtelierWaitingScans,
  lookupAtelierPersonByBracelet,
  createAtelierHandout,
  getAtelierDeskContext,
  listAtelierDeskTeams,
  listAtelierPersonOpenHandouts,
  lookupAtelierDeskPerson,
  returnAtelierPersonLines,
  searchAtelierDeskPersons,
} from "@/lib/api";
import { formatDate, formatDateNl, formatDateTimeNl } from "@/lib/date-time";
import { maskEmail } from "@/lib/mask-email";
import type {
  AtelierDeskContext,
  AtelierDeskPerson,
  AtelierDeskTeam,
  AtelierDeskTeamResponsible,
  AtelierFestival,
  AtelierHandout,
  AtelierScan,
  AtelierScanner,
  Season,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ArticleThumb } from "@/components/module-5/article-management";
import { AtelierFestivalSelect, useAtelierFestival } from "@/components/module-5/atelier-festival-select";
import { AtelierSeasonSelect, useAtelierSeasonId } from "@/components/module-5/atelier-season-select";
import { ATELIER_STOCK_CHANGED_EVENT } from "@/components/module-5/atelier-stock-common";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";
import { atelierDeskErrorMessage } from "@/components/module-5/desk-common";
import { useDeskScanner, writeScanner } from "@/components/module-5/desk-scanner";

type Mode = "pickup" | "return";

/** "Balie 1 (SUN0410)", or the device name/id when it has no label. */
function scannerName(scanner: AtelierScanner) {
  const device = scanner.device_name ?? scanner.device_id;
  return scanner.label ? `${scanner.label} (${device})` : device;
}

/** "Anaïs Wydaeghe". */
function scanPersonName(scan: AtelierScan) {
  return [scan.first_name, scan.last_name].filter(Boolean).join(" ");
}

interface DeskScreenProps {
  seasons: Season[];
  canBook: boolean;
  canCancel: boolean;
}

export function DeskScreen({ seasons, canBook, canCancel }: DeskScreenProps) {
  const t = useTranslations("atelier.desk");
  const seasonId = useAtelierSeasonId(seasons);
  const { festivals, festival } = useAtelierFestival(seasonId);
  const [mode, setMode] = useState<Mode | null>(null);
  // Set by Ophalen's "Eerst terugbrengen" (or a scan): the return opens with this person chosen.
  const [returnPerson, setReturnPerson] = useState<AtelierDeskPerson | null>(null);
  // A scanned person not found for the return: the search starts with their name.
  const [returnQuery, setReturnQuery] = useState("");
  // The scan the current transaction came from (sent along, so it's marked used).
  const [activeScan, setActiveScan] = useState<AtelierScan | null>(null);

  // This desk's scanner and its waiting scans (polled every 2 seconds).
  const scannerId = useDeskScanner();
  const scanners = useKeyedLoad<AtelierScanner[]>("desk-scanners", listAtelierDeskScanners);
  const wristbandRequired = useKeyedLoad<boolean>("wristband-required", getAtelierWristbandRequired).data ?? false;
  const [waiting, setWaiting] = useState<{ deviceId: string; scans: AtelierScan[] } | null>(null);
  useEffect(() => {
    if (!scannerId) return;
    let cancelled = false;
    function poll() {
      listAtelierWaitingScans(scannerId!)
        .then((scans) => {
          if (!cancelled) setWaiting({ deviceId: scannerId!, scans });
        })
        // A failed poll keeps the last known list; the next one tries again.
        .catch(() => undefined);
    }
    poll();
    const timer = window.setInterval(poll, 2000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [scannerId]);
  const waitingScans = (waiting?.deviceId === scannerId ? waiting.scans : []).filter((scan) => scan.id !== activeScan?.id);
  const newestScan = waitingScans[0] ?? null;
  // The chosen day, kept per festival; defaults to today when it's a festival day, else its first day.
  const [dayChoice, setDayChoice] = useState<{ festivalId: number; day: string } | null>(null);
  const today = formatDate(new Date().toISOString());
  const day =
    festival === null
      ? null
      : dayChoice?.festivalId === festival.id
        ? dayChoice.day
        : (festival.days.find((item) => item === today) ?? festival.days[0]);


  // Start a transaction — from the newest waiting scan, when there is one.
  // A return from a scan opens the scanned person (found by wristband at this
  // festival, else by name); not found, the search starts with their name.
  async function start(next: Mode) {
    const scan = newestScan;
    setActiveScan(scan);
    setReturnPerson(null);
    setReturnQuery("");
    if (next === "return" && scan && festival) {
      const byBracelet = scan.wristband_number
        ? await lookupAtelierPersonByBracelet(festival.id, scan.wristband_number).catch(() => null)
        : null;
      const person =
        byBracelet ??
        (scan.first_name && scan.last_name
          ? await lookupAtelierDeskPerson(scan.first_name, scan.last_name, festival.id).catch(() => null)
          : null);
      setReturnPerson(person);
      if (!person) setReturnQuery(scanPersonName(scan));
    }
    setMode(next);
  }

  function finish() {
    setMode(null);
    setReturnPerson(null);
    setReturnQuery("");
    setActiveScan(null);
    window.dispatchEvent(new Event(ATELIER_STOCK_CHANGED_EVENT));
  }

  // Keys 1 / 2 choose Ophalen / Terugbrengen while the choice is shown.
  useEffect(() => {
    if (mode !== null || !canBook || festival === null) return;
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if (event.key === "1") void start("pickup");
      if (event.key === "2") void start("return");
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  // "Negeren": the scan no longer waits at this desk.
  async function dismiss(scan: AtelierScan) {
    await dismissAtelierScan(scan.id).catch(() => undefined);
    setWaiting((current) => (current ? { ...current, scans: current.scans.filter((item) => item.id !== scan.id) } : current));
  }

  return (
    // At least as tall as the space under the topbar (minus the page padding and
    // help link), so the Ophalen / Terugbrengen choice can sit in its middle.
    <div className="flex min-h-[calc(100vh-8rem)] flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <AtelierFestivalSelect festivals={festivals} festival={festival} />
          {festival && day && (
            <div className="flex w-40 flex-col gap-2">
              <Label htmlFor="atelier-desk-day">{t("dayLabel")}</Label>
              <Select
                value={day}
                onValueChange={(value) => value && setDayChoice({ festivalId: festival.id, day: value })}
                disabled={mode !== null}
              >
                <SelectTrigger id="atelier-desk-day">
                  <SelectValue>{(value: string | null) => (value ? formatDateNl(value) : "")}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {festival.days.map((item) => (
                    <SelectItem key={item} value={item}>
                      {formatDateNl(item)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="flex w-56 flex-col gap-2">
            <Label htmlFor="atelier-desk-scanner">{t("scannerLabel")}</Label>
            <Select value={scannerId ?? ""} onValueChange={(value) => writeScanner(value || null)}>
              <SelectTrigger id="atelier-desk-scanner">
                <SelectValue>
                  {(value: string | null) => {
                    const scanner = scanners.data?.find((item) => item.device_id === value);
                    return scanner ? scannerName(scanner) : t("noScanner");
                  }}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {(scanners.data ?? []).map((scanner) => (
                  <SelectItem key={scanner.id} value={scanner.device_id}>
                    {scannerName(scanner)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <AtelierSeasonSelect seasons={seasons} seasonId={seasonId} />
        </div>
      </div>

      {festival === null || day === null ? (
        <p className="text-sm text-muted-foreground">{t("noFestival")}</p>
      ) : !canBook ? (
        <p className="text-sm text-muted-foreground">{t("noRight")}</p>
      ) : mode === null ? (
        // The choice that starts every transaction (for the scanned person, when a scan waits),
        // centred vertically in the rest of the screen.
        <div className="flex flex-1 flex-col justify-center gap-4">
          {newestScan && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border-2 border-primary bg-primary/5 px-4 py-3">
              <div className="flex items-center gap-3">
                <ScanLine className="size-6 text-primary" />
                <div>
                  <p className="text-lg font-semibold">
                    {t("scanned", { name: scanPersonName(newestScan) })}
                    {newestScan.source === "test" && <span className="ml-2 rounded bg-amber-200 px-1.5 text-xs text-amber-900">{t("testBadge")}</span>}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {[
                      newestScan.team_name,
                      newestScan.wristband_number && t("braceletShort", { number: newestScan.wristband_number }),
                      newestScan.size && t("sizeShort", { size: newestScan.size }),
                      formatDateTimeNl(newestScan.received_at),
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  <p className="text-sm font-medium">{t("scanChoose")}</p>
                </div>
              </div>
              <Button variant="ghost" onClick={() => void dismiss(newestScan)}>
                <X className="size-4" />
                {t("dismissScan")}
              </Button>
            </div>
          )}
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <button
            type="button"
            onClick={() => void start("pickup")}
            className="flex min-h-96 flex-col items-center justify-center gap-4 rounded-xl bg-emerald-600 p-8 text-white shadow-md transition hover:bg-emerald-700 focus-visible:ring-4 focus-visible:ring-emerald-300 focus-visible:outline-none"
          >
            <PackagePlus className="size-20" />
            <span className="text-5xl font-bold">{t("pickup")}</span>
            <span className="text-base opacity-90">{t("pickupHint")}</span>
          </button>
          <button
            type="button"
            onClick={() => void start("return")}
            className="flex min-h-96 flex-col items-center justify-center gap-4 rounded-xl bg-sky-600 p-8 text-white shadow-md transition hover:bg-sky-700 focus-visible:ring-4 focus-visible:ring-sky-300 focus-visible:outline-none"
          >
            <PackageMinus className="size-20" />
            <span className="text-5xl font-bold">{t("return")}</span>
            <span className="text-base opacity-90">{t("returnHint")}</span>
          </button>
        </div>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* The chosen kind of transaction stays visible as a coloured bar. */}
          <div
            className={cn(
              "flex items-center justify-between rounded-lg px-4 py-3 text-white",
              mode === "pickup" ? "bg-emerald-600" : "bg-sky-600",
            )}
          >
            <span className="flex items-center gap-2 text-xl font-bold">
              {mode === "pickup" ? <PackagePlus className="size-6" /> : <PackageMinus className="size-6" />}
              {mode === "pickup" ? t("pickup") : t("return")}
              <span className="text-sm font-normal opacity-90">
                · {festival.name} · {formatDateNl(day)}
              </span>
            </span>
            <Button variant="secondary" onClick={finish}>
              {t("cancelTransaction")}
            </Button>
          </div>
          {newestScan && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <ScanLine className="size-4" />
              {t("scanWaiting", { name: scanPersonName(newestScan) })}
            </p>
          )}
          {mode === "pickup" ? (
            <PickupForm
              festival={festival}
              day={day}
              scan={activeScan}
              wristbandRequired={wristbandRequired}
              onDone={finish}
              onReturnFirst={(person) => {
                setReturnPerson(person);
                setMode("return");
              }}
            />
          ) : (
            <ReturnForm
              canCancel={canCancel}
              initialPerson={returnPerson}
              initialQuery={returnQuery}
              scan={activeScan}
              onDone={finish}
            />
          )}
        </div>
      )}
    </div>
  );
}

interface PickupFormProps {
  festival: AtelierFestival;
  day: string;
  /** The wristband scan this pick-up starts from (fills the form in). */
  scan: AtelierScan | null;
  /** The global switch: a wristband number is needed. */
  wristbandRequired: boolean;
  onDone: () => void;
  /** "Eerst terugbrengen": switch to the return of this person. */
  onReturnFirst: (person: AtelierDeskPerson) => void;
}

/** Ophalen: who, which team, and a size per package article taken. */
function PickupForm({ festival, day, scan, wristbandRequired, onDone, onReturnFirst }: PickupFormProps) {
  const t = useTranslations("atelier.desk");
  const tStock = useTranslations("atelier.stock");
  const tFit = useTranslations("atelier.fits");
  // A scan fills the form in (the desk can still change everything).
  const [firstName, setFirstName] = useState(scan?.first_name ?? "");
  const [lastName, setLastName] = useState(scan?.last_name ?? "");
  const [email, setEmail] = useState(scan?.email ?? "");
  // The address the scan or a known worker filled in: while the box still
  // holds it, it's only shown masked (GDPR) until the desk clicks "Wijzig".
  const [prefilledEmail, setPrefilledEmail] = useState(scan?.email ?? "");
  const emailLocked = email !== "" && email === prefilledEmail;
  const [bracelet, setBracelet] = useState(scan?.wristband_number ?? "");
  const [teamChoice, setTeamId] = useState<number | null>(scan?.team_id ?? null);
  // The worker recognised by the typed first + family name (null = a new one).
  const [person, setPerson] = useState<AtelierDeskPerson | null>(null);
  // The desk's choice per article: an article size, or null = explicitly not
  // taken. Articles without a choice fall back to the pre-selection below.
  const [chosen, setChosen] = useState<Record<number, number | null>>({});
  const [isBooking, setIsBooking] = useState(false);

  const teams = useKeyedLoad<AtelierDeskTeam[]>(String(festival.id), () => listAtelierDeskTeams(festival.id));
  // Only a team with a package at this festival counts (a scanned team may have none).
  const teamId = teamChoice !== null && teams.data?.some((team) => team.team_id === teamChoice) ? teamChoice : null;
  const context = useKeyedLoad<AtelierDeskContext>(teamId === null ? null : `${festival.id}-${teamId}-${day}`, () =>
    getAtelierDeskContext(festival.id, teamId!, day),
  );

  // Look the first + family name up (shortly after typing stops): a known
  // worker fills in their email, bracelet number and last team, and shows
  // what they still have.
  useEffect(() => {
    const first = firstName.trim();
    const last = lastName.trim();
    if (!first || !last) return;
    const timer = window.setTimeout(() => {
      lookupAtelierDeskPerson(first, last, festival.id)
        .then((match) => {
          setPerson(match);
          if (match) {
            setEmail((current) => current || (match.email ?? ""));
            setPrefilledEmail((current) => current || (match.email ?? ""));
            setBracelet((current) => current || (match.bracelet_number ?? ""));
            setTeamId((current) => current ?? (teams.data?.some((team) => team.team_id === match.last_team_id) ? match.last_team_id : null));
          }
        })
        .catch(() => setPerson(null));
    }, 350);
    return () => window.clearTimeout(timer);
  }, [firstName, lastName, teams.data, festival.id]);

  const stillOut = new Set((person?.open_lines ?? []).map((line) => line.article_id));
  const articles = context.data?.articles ?? [];

  // The size taken for an article: the desk's choice, else the scanned size
  // (when that size is in stock), else — when exactly one size is in stock
  // (e.g. OneSize) — that size, else none.
  function selectedSize(article: AtelierDeskContext["articles"][number]): number | null {
    if (stillOut.has(article.article_id)) return null;
    if (article.article_id in chosen) return chosen[article.article_id];
    const inStock = article.sizes.filter((size) => size.available > 0);
    const scanned = scan?.size?.trim().toLowerCase();
    const bySize = scanned ? inStock.filter((size) => size.size_name.toLowerCase() === scanned) : [];
    if (bySize.length === 1) return bySize[0].article_size_id;
    return inStock.length === 1 ? inStock[0].article_size_id : null;
  }

  // Click a size to take it, click the chosen size again to skip the article.
  function toggleSize(articleId: number, articleSizeId: number, isSelected: boolean) {
    setChosen((current) => ({ ...current, [articleId]: isSelected ? null : articleSizeId }));
  }

  const lines = articles
    .map((article) => ({ article_id: article.article_id, article_size_id: selectedSize(article) }))
    .filter((line): line is { article_id: number; article_size_id: number } => line.article_size_id !== null);

  // What still keeps "Uitgeven" disabled (null = ready).
  const missing =
    firstName.trim() === "" || lastName.trim() === ""
      ? t("missingName")
      : email.trim() !== "" && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())
        ? t("missingEmail")
        : wristbandRequired && bracelet.trim() === "" && !person
          ? t("missingBracelet")
          : teamId === null
          ? t("missingTeam")
          : lines.length === 0
            ? t("missingArticle")
            : null;
  const ready = missing === null;

  const served = context.data?.served_today ?? 0;
  const reserved = context.data?.persons_reserved ?? 0;

  async function handleSubmit() {
    if (!ready || teamId === null) return;
    setIsBooking(true);
    try {
      const handout = await createAtelierHandout({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim() || null,
        bracelet_number: bracelet.trim() || null,
        scan_id: scan?.id ?? null,
        festival_id: festival.id,
        team_id: teamId,
        day,
        lines,
      });
      toast.success(
        t("handedOut", {
          name: handout.person_name,
          pieces: handout.lines.map((line) => `${line.article_name} ${line.size_name}`).join(", "),
        }),
      );
      onDone();
    } catch (error) {
      toast.error(atelierDeskErrorMessage(t, tStock, error));
      // "Not returned yet": look the person up again so the box and the
      // greyed article show what is still out.
      if (error instanceof ApiError && error.message.startsWith("article_still_out")) {
        lookupAtelierDeskPerson(firstName.trim(), lastName.trim(), festival.id)
          .then(setPerson)
          .catch(() => setPerson(null));
      }
    } finally {
      setIsBooking(false);
    }
  }

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        void handleSubmit();
      }}
    >
      {/* First name and family name first: together they are the person. */}
      <div className="grid max-w-5xl grid-cols-1 gap-4 md:grid-cols-5">
        <div className="flex flex-col gap-2">
          <Label htmlFor="atelier-desk-first-name">
            {t("firstNameLabel")} <span className="text-destructive">*</span>
          </Label>
          <Input
            id="atelier-desk-first-name"
            autoFocus
            autoComplete="off"
            value={firstName}
            onChange={(event) => {
              setFirstName(event.target.value);
              setPerson(null);
            }}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="atelier-desk-last-name">
            {t("lastNameLabel")} <span className="text-destructive">*</span>
          </Label>
          <Input
            id="atelier-desk-last-name"
            autoComplete="off"
            value={lastName}
            onChange={(event) => {
              setLastName(event.target.value);
              setPerson(null);
            }}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="atelier-desk-email">{t("emailLabel")}</Label>
          {emailLocked ? (
            // A filled-in address: masked and read-only; "Wijzig" empties the box for a new one.
            <div className="flex items-center gap-2">
              <span
                id="atelier-desk-email"
                className="flex h-8 min-w-0 flex-1 items-center truncate rounded-lg border bg-muted/50 px-2.5 text-sm text-muted-foreground"
              >
                {maskEmail(email)}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => {
                  setEmail("");
                  setPrefilledEmail("");
                }}
              >
                {t("changeEmail")}
              </Button>
            </div>
          ) : (
            <Input
              id="atelier-desk-email"
              type="email"
              autoComplete="off"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          )}
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="atelier-desk-bracelet">
            {t("braceletLabel")}
            {wristbandRequired && <span className="text-destructive"> *</span>}
          </Label>
          <Input
            id="atelier-desk-bracelet"
            autoComplete="off"
            value={bracelet}
            onChange={(event) => setBracelet(event.target.value)}
          />
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="atelier-desk-team">
            {t("teamLabel")} <span className="text-destructive">*</span>
          </Label>
          <Select
            value={teamId !== null ? String(teamId) : ""}
            onValueChange={(value) => {
              setTeamId(value ? Number(value) : null);
              setChosen({});
            }}
          >
            <SelectTrigger id="atelier-desk-team">
              <SelectValue>
                {(value: string | null) =>
                  teams.data?.find((team) => String(team.team_id) === value)?.team_name ?? t("pickTeam")
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {(teams.data ?? []).map((team) => (
                <SelectItem key={team.team_id} value={String(team.team_id)}>
                  {team.team_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* "Gekend: …" on the left, the team's leads behind an icon on the right. */}
      {(person || context.data) && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm text-muted-foreground">
            {person && t("knownPerson", { name: person.name })}
            {person?.bracelet_number && ` · ${t("braceletShort", { number: person.bracelet_number })}`}
          </p>
          {teamId !== null && context.data && (
            <TeamResponsiblesButton teamName={context.data.team_name} responsibles={context.data.team_responsibles} />
          )}
        </div>
      )}

      {/* What the person still has: those articles can't be picked up again until returned. */}
      {person && person.open_lines.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-orange-300 bg-orange-50 px-4 py-3 text-orange-800 dark:border-orange-500/40 dark:bg-orange-500/10 dark:text-orange-200">
          <div className="flex items-start gap-2">
            <TriangleAlert className="mt-0.5 size-5 shrink-0" />
            <div>
              <p className="font-medium">{t("stillHasTitle", { name: person.name })}</p>
              <ul className="text-sm">
                {person.open_lines.map((line) => (
                  <li key={line.line_id}>
                    {line.article_name} · {line.size_name} · {tFit(line.fit)} —{" "}
                    {t("handedOutAt", { moment: formatDateTimeNl(line.handed_out_at) })}
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <Button type="button" className="bg-sky-600 hover:bg-sky-700" onClick={() => onReturnFirst(person)}>
            <PackageMinus className="size-4" />
            {t("returnFirst")}
          </Button>
        </div>
      )}

      {teamId !== null && context.data && (
        <p
          className={cn(
            "flex items-center gap-2 text-sm",
            served >= reserved ? "font-medium text-orange-700 dark:text-orange-300" : "text-muted-foreground",
          )}
        >
          {served >= reserved && <TriangleAlert className="size-4" />}
          {t("servedToday", { served, reserved })}
        </p>
      )}

      {teamId !== null && (
        <div className="flex flex-col gap-3">
          {context.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
          {context.data && articles.length === 0 && <p className="text-sm text-destructive">{t("noPackage")}</p>}
          {articles.map((article) => {
            const out = stillOut.has(article.article_id);
            return (
              <Card key={article.article_id} className={out ? "opacity-50" : undefined}>
                <CardContent className="flex flex-wrap items-center gap-4">
                  {/* Wrapped: the thumb centres itself (mx-auto), which in this row would push the rest away. */}
                  <div className="shrink-0">
                    <ArticleThumb article={{ id: article.article_id, ...article }} />
                  </div>
                  <div className="w-48">
                    <p className="font-medium">{article.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {out ? t("notBackYet") : selectedSize(article) === null ? t("notTaken") : t("onePiece")}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {/* An article without active sizes can't be handed out: say how to fix it. */}
                    {article.sizes.length === 0 && <p className="text-sm text-destructive">{t("noSizes")}</p>}
                    {article.sizes.map((size) => {
                      const selected = selectedSize(article) === size.article_size_id;
                      return (
                        <Button
                          key={size.article_size_id}
                          type="button"
                          size="lg"
                          variant={selected ? "default" : "outline"}
                          disabled={out || (size.available === 0 && !selected)}
                          onClick={() => toggleSize(article.article_id, size.article_size_id, selected)}
                        >
                          {size.size_name} · {tFit(size.fit)}
                          <span className="text-xs opacity-70">({size.available})</span>
                        </Button>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="lg" className="bg-emerald-600 text-lg hover:bg-emerald-700" disabled={!ready || isBooking}>
          <PackagePlus className="size-5" />
          {t("handOutCount", { count: lines.length })}
        </Button>
        {/* Why the button is still disabled. */}
        {missing && <span className="text-sm text-muted-foreground">{missing}</span>}
      </div>
    </form>
  );
}

interface TeamResponsiblesButtonProps {
  teamName: string;
  responsibles: AtelierDeskTeamResponsible[];
}

/** An icon that opens the team's leads (name, phone, email, comments) — not shown until clicked. */
function TeamResponsiblesButton({ teamName, responsibles }: TeamResponsiblesButtonProps) {
  const t = useTranslations("atelier.desk");
  return (
    <Dialog>
      <DialogTrigger
        render={
          <Button type="button" variant="outline" size="icon" title={t("teamResponsibles")} aria-label={t("teamResponsibles")} />
        }
      >
        <Contact className="size-4" />
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("teamResponsiblesTitle", { team: teamName })}</DialogTitle>
        </DialogHeader>
        {responsibles.length === 0 && <p className="text-sm text-muted-foreground">{t("noTeamResponsibles")}</p>}
        <ul className="flex flex-col gap-3">
          {responsibles.map((responsible, index) => (
            <li key={index} className="rounded-md border px-3 py-2 text-sm">
              <p className="font-medium">{responsible.name}</p>
              <p>
                <a href={`tel:${responsible.phone}`} className="text-primary hover:underline">
                  {responsible.phone}
                </a>
                {" · "}
                <a href={`mailto:${responsible.email}`} className="text-primary hover:underline">
                  {responsible.email}
                </a>
              </p>
              {responsible.comments && <p className="text-muted-foreground">{responsible.comments}</p>}
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}

interface ReturnFormProps {
  canCancel: boolean;
  /** Opens with this person chosen (from Ophalen's "Eerst terugbrengen" or a scan). */
  initialPerson: AtelierDeskPerson | null;
  /** A scanned person not found: the search starts with this text. */
  initialQuery: string;
  /** The wristband scan this return starts from (marked used by the first booking). */
  scan: AtelierScan | null;
  onDone: () => void;
}

/** Terugbrengen: find the person, tick what came back. */
function ReturnForm({ canCancel, initialPerson, initialQuery, scan, onDone }: ReturnFormProps) {
  const t = useTranslations("atelier.desk");
  const tStock = useTranslations("atelier.stock");
  const tFit = useTranslations("atelier.fits");
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<AtelierDeskPerson[]>([]);
  const [person, setPerson] = useState<AtelierDeskPerson | null>(initialPerson);
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

  // Search shortly after typing stops (at least 2 characters); only people with pieces out.
  useEffect(() => {
    const value = query.trim();
    if (value.length < 2) return;
    const timer = window.setTimeout(() => {
      searchAtelierDeskPersons(value)
        .then((found) => setResults(found.filter((item) => item.open_lines.length > 0)))
        .catch(() => setResults([]));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [query]);

  function choose(item: AtelierDeskPerson) {
    setPerson(item);
    setUnticked([]);
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
        await returnAtelierPersonLines(person.id, ticked, scan?.id ?? null);
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
                  <label key={line.id} className="flex items-center gap-3 text-base">
                    <Checkbox
                      checked={ticked.includes(line.id)}
                      onCheckedChange={(checked) =>
                        setUnticked((current) => (checked === true ? current.filter((id) => id !== line.id) : [...current, line.id]))
                      }
                    />
                    {line.article_name} · {line.size_name} · {tFit(line.fit)}
                  </label>
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
        <Button variant="outline" size="lg" onClick={() => setPerson(null)}>
          {t("otherPerson")}
        </Button>
      </div>
    </div>
  );
}
