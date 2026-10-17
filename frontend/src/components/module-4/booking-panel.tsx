"use client";

// StockMaster's booking panel: ONE screen for Inboeken, Kar laden,
// Uitboeken, Kar vertrekt, Kar terug and Kar uitladen, pre-set for the
// action of the page it's on (Telling has its own screen, count-panel.tsx).
// The person never chooses "from/to": the action decides it. Above the
// title, the process bar (process-flow.tsx) shows where the screen sits in
// the warehouse process (not on Uitboeken, which is outside that flow).
//
// It works like a basket: type a few letters of a product (the search shows
// its bin and stock), Enter, type the quantity, Enter — the line is added
// and the cursor is back in the search. Every line shows "before → after"
// for each place it touches, and a quantity above what's available is
// flagged in plain words. One "Bevestigen" (or Ctrl+Enter) books it all,
// under the logged-in user; the toast then offers "Ongedaan maken".
//
// Smart pre-filling:
// - Kar laden: the kar's missing needs (need − already in the kar);
// - Kar uitladen: "Alles uitladen";
// - Kar terug: what left with the kar, each line going back into the kar or
//   to free stock as the product is set up, so only differences are typed;
// - Inboeken from "Te bestellen": ?prefill=<product>:<qty>,...;
// - Inboeken from a TagScan scan: ?tagscan=<file ids> (from the "scans
//   waiting" dialog) puts those files' "Book In" lines in the basket, like
//   the Excel upload; the booking then marks those scan lines "loaded";
// - ?kar=<id> and ?product=<id> from the buttons on the other screens.
//
// Kar laden opens on a loading overview of every kar (kar-load-overview.tsx,
// switched by kar-load-screen.tsx); its "Laden" button opens this panel
// with ?kar=<id>, and a link here leads back to that overview. With a kar
// chosen, Kar laden shows the kar as a header and ONE table of its products
// (kar-load-table.tsx) with a compact reference/comment/confirm bar above
// it; "Nu te leveren" starts at 0 and is typed, or filled for the checked
// rows by "Vul aan met wat ontbreekt"; products are added by hand in a pop-up.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, FileSpreadsheet, FileText, ListPlus, PackageOpen, ScanLine, Trash2, Upload, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Link, usePathname, useRouter } from "@/i18n/navigation";
import {
  addStockMasterManualRequest,
  createStockMasterBooking,
  deleteStockMasterManualRequest,
  getStockMasterKar,
  getStockMasterLookups,
  getStockMasterStock,
  importStockMasterBookIn,
  listStockMasterKars,
  listStockMasterTagscanBookIn,
  reverseStockMasterBooking,
  stockMasterBookingPdfUrl,
  stockMasterBookInTemplateUrl,
} from "@/lib/api";
import type {
  Season,
  StockMasterAction,
  StockMasterBookInImport,
  StockMasterDocument,
  StockMasterKarDetail,
  StockMasterKarSummary,
  StockMasterLookups,
  StockMasterMyPermissions,
  StockMasterProductStock,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Dialog, DialogClose, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { KarLoadHeader } from "@/components/module-4/kar-load-sections";
import {
  KarLoadTable,
  buildKarLoadRows,
  fillCheckedRows,
  karLoadRowKey,
  type KarLoadRow,
  type KarLoadSource,
} from "@/components/module-4/kar-load-table";
import { ProcessFlow, isProcessFlowAction } from "@/components/module-4/process-flow";
import { ProductThumb } from "@/components/module-4/product-thumb";
import { KarSearch, ProductSearch, SelectedKar } from "@/components/module-4/stock-pickers";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import {
  ACTION_PATHS,
  STOCKMASTER_BASE,
  announceStockChanged,
  hasRight,
  stockErrorMessage,
} from "@/components/module-4/stockmaster-common";
import { openTagscanBookInDialog } from "@/components/module-4/tagscan-book-in-banner";

interface BookingPanelProps {
  action: Exclude<StockMasterAction, "count">;
  seasons: Season[];
  permissions: StockMasterMyPermissions;
}

/** One line in the basket. */
interface BasketLine {
  productId: number;
  quantity: number;
  /** Only on "Kar terug": back into the kar or to free stock. */
  destination?: "kar" | "free";
  /** Only on "Kar terug": how many left with the kar. */
  dispatched?: number;
  /** Only on Kar laden: "manual" for a Manueel row; none for the product's kar-need row. A product
   *  can have one line of each, booked together. */
  source?: KarLoadSource;
}

/** A scanned line that couldn't go into the basket (Inboeken from a scan). */
interface ScanProblem {
  lineId: number;
  filename: string;
  lineNumber: number;
  detail: string;
}

/** Add imported lines (Excel or scan) to the basket, summing a product already there. */
function mergeIntoBasket(current: BasketLine[], imported: { product_id: number; quantity: number }[]): BasketLine[] {
  const merged = [...current];
  for (const line of imported) {
    const index = merged.findIndex((existing) => existing.productId === line.product_id);
    if (index >= 0) merged[index] = { ...merged[index], quantity: merged[index].quantity + line.quantity };
    else merged.push({ productId: line.product_id, quantity: line.quantity });
  }
  return merged;
}

/** "Before → after" of one place a line touches. */
interface PlaceChange {
  label: string;
  before: number;
  after: number;
}

// Sentinel for "free stock" in the source dropdowns (Base UI needs a value).
const FREE_SOURCE = "free";
const NO_SELECTION = "none";

export function BookingPanel({ action, seasons, permissions }: BookingPanelProps) {
  const t = useTranslations("stockMaster");
  const tAction = useTranslations(`stockMaster.actions.${action}`);
  const locale = useLocale();
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const seasonId = useStockMasterSeasonId(seasons);
  const season = seasons.find((item) => item.id === seasonId) ?? null;

  const isKarAction = action !== "book_in" && action !== "book_out";
  const usesBasket = action !== "kar_dispatch";

  // --- Data -----------------------------------------------------------------
  const [stock, setStock] = useState<StockMasterProductStock[]>([]);
  const [kars, setKars] = useState<StockMasterKarSummary[]>([]);
  const [lookups, setLookups] = useState<StockMasterLookups | null>(null);
  // The last loaded kar detail; only used while it belongs to the chosen kar.
  const [loadedKarDetail, setLoadedKarDetail] = useState<StockMasterKarDetail | null>(null);

  // --- Form -----------------------------------------------------------------
  // The kar the action is about (or, on Uitboeken, the kar taken out of).
  const [karId, setKarId] = useState<number | null>(() => Number(searchParams.get("kar")) || null);
  // Kar laden from another kar instead of free stock.
  const [fromKarId, setFromKarId] = useState<number | null>(() => Number(searchParams.get("from")) || null);
  const [lines, setLines] = useState<BasketLine[]>(() => parsePrefill(searchParams.get("prefill")));
  const [reference, setReference] = useState("");
  const [comment, setComment] = useState("");
  const [reasonId, setReasonId] = useState<number | null>(null);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [festivalId, setFestivalId] = useState<number | null>(null);
  const [pendingProduct, setPendingProduct] = useState<StockMasterProductStock | null>(null);
  const [pendingQuantity, setPendingQuantity] = useState("1");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastBooking, setLastBooking] = useState<StockMasterDocument | null>(null);
  // Inboeken from Excel: busy flag, and the rows of the last upload that couldn't be used.
  const [isImporting, setIsImporting] = useState(false);
  const [importErrors, setImportErrors] = useState<StockMasterBookInImport["errors"]>([]);
  const importInputRef = useRef<HTMLInputElement>(null);
  // Inboeken from a TagScan scan: the scan lines the basket came from (sent
  // with the booking, which marks them "loaded"), their file names, and the
  // scanned lines that couldn't be used.
  const [scanLineIds, setScanLineIds] = useState<number[]>([]);
  const [scanFilenames, setScanFilenames] = useState<string[]>([]);
  const [scanProblems, setScanProblems] = useState<ScanProblem[]>([]);
  // The ?tagscan= value already loaded, so it's used only once.
  const scanParamUsed = useRef<string | null>(null);
  // The kar whose needs/contents were already put in the basket.
  const prefilledForKar = useRef<number | null>(null);
  // Kar laden: the checked rows of the table (row keys) and the "Manueel product toevoegen" pop-up.
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [isManualOpen, setIsManualOpen] = useState(false);

  const searchRef = useRef<HTMLInputElement>(null);
  const quantityRef = useRef<HTMLInputElement>(null);

  const productsById = useMemo(() => new Map(stock.map((product) => [product.product_id, product])), [stock]);
  const selectedKar = kars.find((kar) => kar.kar_id === karId) ?? null;
  const fromKar = kars.find((kar) => kar.kar_id === fromKarId) ?? null;
  const karDetail =
    isKarAction && loadedKarDetail !== null && loadedKarDetail.kar.kar_id === karId ? loadedKarDetail : null;
  // Kar laden with a chosen kar: the kar shows as a header with its contents and what's still to load.
  const showsKarLoadHeader = action === "kar_load" && karDetail !== null;
  // Kar laden: the rows of the "Karinhoud" table (needs, manual products, kar contents).
  const karRows = useMemo(
    () => (action === "kar_load" && karDetail ? buildKarLoadRows(karDetail, lines, productsById) : []),
    [action, karDetail, lines, productsById],
  );
  const canUndo = hasRight(permissions, "bookings", "delete");
  const canSeeBookings = hasRight(permissions, "bookings", "view");
  const seasonLocked =
    season !== null && !season.periode_open && !permissions.editable_screen_keys.includes("stockmaster.closedseason");

  // A product passed in the URL (?product=) is made ready for its quantity
  // once, as soon as the products have arrived.
  const productParamUsed = useRef(false);

  // --- Loading --------------------------------------------------------------

  const reloadStock = useCallback(() => {
    getStockMasterStock()
      .then((products) => {
        setStock(products);
        const productParam = Number(searchParams.get("product")) || null;
        if (productParam !== null && !productParamUsed.current) {
          productParamUsed.current = true;
          const product = products.find((item) => item.product_id === productParam);
          if (product) {
            setPendingProduct(product);
            // On Kar laden the product entry lives in the "Manueel product toevoegen" pop-up.
            if (action === "kar_load") setIsManualOpen(true);
            window.setTimeout(() => quantityRef.current?.select(), 50);
          }
        }
      })
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [t, searchParams, action]);

  useEffect(() => {
    reloadStock();
    getStockMasterLookups()
      .then(setLookups)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [reloadStock, t]);

  const reloadKars = useCallback(() => {
    listStockMasterKars(seasonId)
      .then(setKars)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [seasonId, t]);

  useEffect(() => {
    reloadKars();
  }, [reloadKars]);

  /** Pre-fill the basket once per chosen kar: what left with the kar on Kar
   *  terug, and the kar's team/festival on Kar vertrekt. (Kar laden starts
   *  with "Nu te leveren" at 0: it's typed or filled with "Vul aan met wat
   *  ontbreekt".) */
  const prefillFor = useCallback(
    (detail: StockMasterKarDetail) => {
      if (prefilledForKar.current === detail.kar.kar_id) return;
      prefilledForKar.current = detail.kar.kar_id;
      if (action === "kar_return") {
        setLines(
          detail.dispatched.map((line) => ({
            productId: line.product_id,
            quantity: line.quantity,
            dispatched: line.quantity,
            destination: line.stock_return_to,
          })),
        );
      } else if (action === "kar_dispatch") {
        setTeamId(detail.kar.team_id);
        setFestivalId(detail.festivals.length === 1 ? detail.festivals[0].id : null);
      }
    },
    [action],
  );

  const reloadKarDetail = useCallback(() => {
    if (karId === null || !isKarAction) return;
    getStockMasterKar(karId, seasonId)
      .then((detail) => {
        setLoadedKarDetail(detail);
        prefillFor(detail);
      })
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [karId, seasonId, isKarAction, prefillFor, t]);

  useEffect(() => {
    reloadKarDetail();
  }, [reloadKarDetail]);

  // Kar laden: another season in the dropdown means other needs, so the table starts over
  // (manual pieces and checks included). Not on the first render, so ?prefill=/?product= stay.
  // Adjusted while rendering (React's pattern for state that follows a changed value).
  const [linesSeasonId, setLinesSeasonId] = useState(seasonId);
  if (linesSeasonId !== seasonId) {
    setLinesSeasonId(seasonId);
    if (action === "kar_load") {
      setLines([]);
      setSelectedIds(new Set());
    }
  }

  // --- Availability and preview ---------------------------------------------

  /** How many pieces of a product are available at the line's source, or
   *  null when there's no limit (Inboeken, Kar terug). */
  function availableFor(product: StockMasterProductStock): number | null {
    const inKar = (id: number | null) => product.kars.find((kar) => kar.kar_id === id)?.quantity ?? 0;
    switch (action) {
      case "book_out":
        return karId !== null ? inKar(karId) : product.free;
      case "kar_load":
        return fromKarId !== null ? inKar(fromKarId) : product.free;
      case "kar_unload":
        return inKar(karId);
      default:
        return null;
    }
  }

  /** The places a line touches, with their quantity before and after. */
  function placeChanges(line: BasketLine, product: StockMasterProductStock): PlaceChange[] {
    const inKar = (id: number | null) => product.kars.find((kar) => kar.kar_id === id)?.quantity ?? 0;
    const free = { label: t("common.freeStock"), before: product.free };
    const kar = (id: number | null, nummer: string | undefined) => ({
      label: nummer ?? "?",
      before: inKar(id),
    });
    const quantity = line.quantity;
    switch (action) {
      case "book_in":
        return [{ ...free, after: free.before + quantity }];
      case "book_out": {
        const source = karId !== null ? kar(karId, selectedKar?.kar_nummer) : free;
        return [{ ...source, after: source.before - quantity }];
      }
      case "kar_load": {
        const source = fromKarId !== null ? kar(fromKarId, fromKar?.kar_nummer) : free;
        // A kar that's out: the pieces join what left with it (a follow-up delivery).
        const target = selectedKar?.is_out
          ? {
              label: t("karLoad.onTheWay", { kar: selectedKar.kar_nummer }),
              before: karDetail?.dispatched.find((item) => item.product_id === product.product_id)?.quantity ?? 0,
            }
          : kar(karId, selectedKar?.kar_nummer);
        return [
          { ...source, after: source.before - quantity },
          { ...target, after: target.before + quantity },
        ];
      }
      case "kar_unload": {
        const source = kar(karId, selectedKar?.kar_nummer);
        return [
          { ...source, after: source.before - quantity },
          { ...free, after: free.before + quantity },
        ];
      }
      case "kar_return": {
        if (quantity === 0) return [];
        const target = line.destination === "free" ? free : kar(karId, selectedKar?.kar_nummer);
        return [{ ...target, after: target.before + quantity }];
      }
      default:
        return [];
    }
  }

  /** A friendly problem with one line, or null when it's fine. */
  function lineProblem(line: BasketLine, product: StockMasterProductStock): string | null {
    if (action !== "kar_return" && line.quantity < 1) return t("booking.quantityTooLow");
    const available = availableFor(product);
    if (available !== null && line.quantity > available) {
      const place =
        action === "kar_unload" || (action === "book_out" && karId !== null)
          ? selectedKar?.kar_nummer
          : action === "kar_load" && fromKarId !== null
            ? fromKar?.kar_nummer
            : t("common.freeStock");
      return t("booking.notEnough", { count: available, place: place ?? "" });
    }
    if ((action === "book_in" || action === "kar_load") && product.is_blocked) return t("booking.blocked");
    return null;
  }

  // --- Basket actions -------------------------------------------------------

  function choosePendingProduct(product: StockMasterProductStock) {
    setPendingProduct(product);
    setPendingQuantity("1");
    window.setTimeout(() => quantityRef.current?.select(), 0);
  }

  function addPendingLine() {
    if (!pendingProduct) return;
    const quantity = Number.parseInt(pendingQuantity, 10);
    if (!Number.isFinite(quantity) || quantity < (action === "kar_return" ? 0 : 1)) {
      toast.error(t("booking.quantityTooLow"));
      return;
    }
    // Kar laden: a manual product is stored as a manual request of the kar (season + kar) and
    // shows as its own "Manueel" row (also when the product has a kar-need row: the Bron
    // differs). It raises that row's "Gevraagd", not "Nu te leveren" (typed or filled by
    // "Vul aan met wat ontbreekt"). Then the pop-up closes.
    if (action === "kar_load") {
      void addManualRequest(pendingProduct, quantity);
      return;
    }
    setLines((current) => {
      const existing = current.find((line) => line.productId === pendingProduct.product_id);
      if (existing) {
        return current.map((line) =>
          line === existing ? { ...line, quantity: line.quantity + quantity } : line,
        );
      }
      return [
        ...current,
        {
          productId: pendingProduct.product_id,
          quantity,
          ...(action === "kar_return" ? { destination: pendingProduct.stock_return_to, dispatched: 0 } : {}),
        },
      ];
    });
    setPendingProduct(null);
    setPendingQuantity("1");
    window.setTimeout(() => searchRef.current?.focus(), 0);
  }

  /** Inboeken from Excel: the file's lines go into the basket (adding to a
   *  product already there); nothing is booked until the person confirms. */
  async function importExcel(file: File) {
    setIsImporting(true);
    try {
      const result = await importStockMasterBookIn(file);
      setLines((current) => mergeIntoBasket(current, result.lines));
      setImportErrors(result.errors);
      if (result.lines.length > 0) toast.success(t("booking.importAdded", { count: result.lines.length }));
      else toast.info(t("booking.importAdded", { count: 0 }));
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    } finally {
      setIsImporting(false);
    }
  }

  /** Inboeken from a TagScan scan: ?tagscan=<file ids> puts those files'
   *  waiting "Book In" lines in the basket (once per value), then drops
   *  the parameter from the address so a reload doesn't add them again. */
  const scanParam = action === "book_in" ? searchParams.get("tagscan") : null;
  useEffect(() => {
    if (!scanParam || scanParam === "open" || scanParamUsed.current === scanParam) return;
    scanParamUsed.current = scanParam;
    const headerIds = new Set(scanParam.split(",").map(Number).filter(Boolean));

    listStockMasterTagscanBookIn()
      .then((files) => {
        // Only files not linked yet: the same scan never goes in twice.
        const chosen = files.filter(
          (file) => headerIds.has(file.header_data_id) && !scanFilenames.includes(file.filename),
        );
        const imported = chosen.flatMap((file) => file.lines);
        setLines((current) => mergeIntoBasket(current, imported));
        setScanLineIds((current) => [...current, ...chosen.flatMap((file) => file.line_ids)]);
        setScanFilenames((current) => [...current, ...chosen.map((file) => file.filename)]);
        setScanProblems((current) => [
          ...current,
          ...chosen.flatMap((file) =>
            file.problems.map((problem) => ({
              lineId: problem.line_id,
              filename: file.filename,
              lineNumber: problem.line_number,
              detail: problem.detail,
            })),
          ),
        ]);
        const productCount = new Set(imported.map((line) => line.product_id)).size;
        if (productCount > 0) toast.success(t("booking.scanAdded", { count: productCount }));
        else toast.info(t("booking.scanAdded", { count: 0 }));
      })
      .catch((error) => toast.error(stockErrorMessage(t, error)))
      .finally(() => {
        const params = new URLSearchParams(searchParams.toString());
        params.delete("tagscan");
        const query = params.toString();
        router.replace(query ? `${pathname}?${query}` : pathname);
      });
  }, [scanParam, scanFilenames, searchParams, router, pathname, t]);

  /** Stop linking the basket to the scan: its lines stay waiting in TagScan. */
  function dropScanLink() {
    setScanLineIds([]);
    setScanFilenames([]);
    setScanProblems([]);
  }

  /** One problem row of the upload as readable text ("code|param" → translation). */
  function importErrorText(detail: string): string {
    const [code, param = ""] = detail.split("|");
    return t.has(`booking.importErrors.${code}`) ? t(`booking.importErrors.${code}`, { p1: param }) : detail;
  }

  function updateLine(productId: number, changes: Partial<BasketLine>) {
    setLines((current) => current.map((line) => (line.productId === productId ? { ...line, ...changes } : line)));
  }

  function removeLine(productId: number) {
    setLines((current) => current.filter((line) => line.productId !== productId));
  }

  /** Kar laden: set "Nu te leveren" of rows (by row key), adding a row's basket line when it has none yet. */
  function setRowQuantities(quantities: Map<string, number>) {
    setLines((current) => {
      const lineKey = (line: BasketLine) => karLoadRowKey(line.productId, line.source);
      const updated = current.map((line) =>
        quantities.has(lineKey(line)) ? { ...line, quantity: quantities.get(lineKey(line)) ?? 0 } : line,
      );
      const existing = new Set(current.map(lineKey));
      const added = karRows
        .filter((row) => quantities.has(row.key) && !existing.has(row.key))
        .map((row) => ({ productId: row.productId, quantity: quantities.get(row.key) ?? 0, source: row.lineSource }));
      return [...updated, ...added];
    });
  }

  /** Kar laden: "Vul aan met wat ontbreekt" fills the checked rows (see fillCheckedRows). */
  function fillMissing() {
    setRowQuantities(fillCheckedRows(karRows, selectedIds));
  }

  /** Kar laden: store a manual request ("Manueel product toevoegen"), then show it. */
  async function addManualRequest(product: StockMasterProductStock, quantity: number) {
    if (karId === null || seasonId === null) return;
    try {
      await addStockMasterManualRequest(karId, { season_id: seasonId, product_id: product.product_id, quantity });
      toast.success(t("karLoad.manualAdded", { quantity, name: product.name }));
      setPendingProduct(null);
      setPendingQuantity("1");
      setIsManualOpen(false);
      reloadKarDetail();
    } catch (error) {
      // The pop-up stays open so the person can correct it.
      toast.error(stockErrorMessage(t, error));
    }
  }

  /** Kar laden: delete the stored manual requests of these Manueel rows, and their
   *  "Nu te leveren" and checks with them. */
  async function removeManualRows(rows: KarLoadRow[]) {
    if (karId === null) return;
    const keys = new Set(rows.map((row) => row.key));
    try {
      for (const row of rows) {
        if (row.requestId !== null) await deleteStockMasterManualRequest(karId, row.requestId);
      }
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    }
    setLines((current) => current.filter((line) => !keys.has(karLoadRowKey(line.productId, line.source))));
    setSelectedIds((current) => new Set([...current].filter((key) => !keys.has(key))));
    reloadKarDetail();
  }

  /** Kar laden: "Verwijder geselecteerde": checked Manueel rows are deleted, the other checked
   *  rows go back to 0 (they hold a need or kar contents). */
  function removeSelected() {
    const manualRows = karRows.filter((row) => row.source === "manual" && selectedIds.has(row.key));
    const resetKeys = new Set(
      karRows.filter((row) => row.source !== "manual" && selectedIds.has(row.key)).map((row) => row.key),
    );
    setLines((current) =>
      current.map((line) => (resetKeys.has(karLoadRowKey(line.productId, line.source)) ? { ...line, quantity: 0 } : line)),
    );
    setSelectedIds(new Set());
    if (manualRows.length > 0) void removeManualRows(manualRows);
  }

  function toggleRow(key: string, checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(key);
      else next.delete(key);
      return next;
    });
  }

  function fillEverything() {
    if (!karDetail) return;
    setLines(
      karDetail.lines
        .filter((line) => line.in_kar > 0)
        .map((line) => ({ productId: line.product_id, quantity: line.in_kar })),
    );
  }

  function chooseKar(kar: StockMasterKarSummary | null) {
    setKarId(kar?.kar_id ?? null);
    prefilledForKar.current = null;
    setSelectedIds(new Set());
    // Return lines belong to one kar; other baskets stay.
    if (action === "kar_return" || action === "kar_unload") setLines([]);
  }

  // --- Booking --------------------------------------------------------------

  const reasons = (lookups?.reasons ?? []).filter(
    (reason) => reason.applies_to === null || reason.applies_to === action,
  );
  // The lines that get booked. On Kar laden a product can be on two rows (kar need + Manueel):
  // they're booked, checked and previewed as one line per product.
  const positiveLines = lines.filter((line) => line.quantity > 0);
  const activeLines =
    action === "kar_return" ? lines : action === "kar_load" ? totalPerProduct(positiveLines) : positiveLines;
  // Kar laden: a table row's product with its total "Nu te leveren" over all its rows (for the checks and preview).
  const productTotal = (row: KarLoadRow): BasketLine => ({
    productId: row.productId,
    quantity: activeLines.find((line) => line.productId === row.productId)?.quantity ?? 0,
  });
  const problems = activeLines.some((line) => {
    const product = productsById.get(line.productId);
    return !product || lineProblem(line, product) !== null;
  });
  const missingKar = isKarAction && karId === null;
  const missingReason = action === "book_out" && reasonId === null;
  const emptyBasket = usesBasket && action !== "kar_return" && activeLines.length === 0;
  const canSubmit =
    seasonId !== null && !seasonLocked && !missingKar && !missingReason && !emptyBasket && !problems && !isSubmitting;

  async function handleSubmit() {
    if (!canSubmit || seasonId === null) return;
    setIsSubmitting(true);
    try {
      const document = await createStockMasterBooking({
        action,
        season_id: seasonId,
        kar_id: action === "book_in" ? null : karId,
        from_kar_id: action === "kar_load" ? fromKarId : null,
        team_id: action === "kar_dispatch" ? teamId : null,
        festival_id: action === "kar_dispatch" ? festivalId : null,
        reference: reference.trim() || null,
        reason_id: reasonId,
        comment: comment.trim() || null,
        tagscan_line_ids: action === "book_in" ? scanLineIds : [],
        lines: usesBasket
          ? activeLines
              .filter((line) => action !== "kar_return" || line.quantity > 0)
              .map((line) => ({ product_id: line.productId, quantity: line.quantity, destination: line.destination }))
          : [],
      });
      setLastBooking(document);
      toast.success(t("booking.booked", { number: document.doc_number }), {
        action: canUndo ? { label: t("booking.undo"), onClick: () => void undo(document) } : undefined,
      });
      // Start the next booking with a clean basket.
      setLines([]);
      setSelectedIds(new Set());
      dropScanLink();
      setReference("");
      setComment("");
      setReasonId(null);
      prefilledForKar.current = karId;
      if (action === "kar_dispatch" || action === "kar_return") setKarId(null);
      reloadStock();
      reloadKars();
      reloadKarDetail();
      announceStockChanged();
      window.setTimeout(() => searchRef.current?.focus(), 0);
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function undo(document: StockMasterDocument) {
    try {
      const reversal = await reverseStockMasterBooking(document.id);
      toast.success(t("booking.undone", { number: document.doc_number }));
      setLastBooking(reversal);
      reloadStock();
      reloadKars();
      reloadKarDetail();
      announceStockChanged();
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    }
  }

  // Ctrl+Enter anywhere in the panel books.
  function handleKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  // --- Rendering --------------------------------------------------------------

  // Which kars can be picked for this action.
  // (Kar laden takes a kar that's out too: that's a follow-up delivery to the festival.)
  const karDisabled = (kar: StockMasterKarSummary) =>
    action === "kar_return" ? !kar.is_out : action === "kar_load" ? false : kar.is_out;

  // The product entry row (product, quantity, add, fill up) and its keyboard hint. On Kar laden it
  // sits in the "Manueel product toevoegen" pop-up; elsewhere on top of the basket card.
  const productEntry = (
    <>
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex min-w-64 flex-1 flex-col gap-2">
          <Label htmlFor="booking-product">{t("booking.productLabel")}</Label>
          {pendingProduct ? (
            <div className="flex h-8 items-center gap-2 rounded-md border bg-muted/40 px-3 text-sm">
              <span className="font-medium">{pendingProduct.name}</span>
              <span className="text-muted-foreground">{pendingProduct.bin_label}</span>
              <button
                type="button"
                className="ml-auto text-xs text-muted-foreground underline"
                onClick={() => {
                  setPendingProduct(null);
                  window.setTimeout(() => searchRef.current?.focus(), 0);
                }}
              >
                {t("booking.otherProduct")}
              </button>
            </div>
          ) : (
            <ProductSearch
              id="booking-product"
              ref={searchRef}
              products={stock}
              onSelect={choosePendingProduct}
              blockBlocked={action === "book_in" || action === "kar_load"}
              karId={action === "kar_load" ? (fromKarId ?? karId) : karId}
              autoFocus={!isKarAction}
            />
          )}
        </div>
        <div className="flex w-28 flex-col gap-2">
          <Label htmlFor="booking-quantity">{t("booking.quantityLabel")}</Label>
          <Input
            id="booking-quantity"
            ref={quantityRef}
            type="number"
            min={action === "kar_return" ? 0 : 1}
            step={1}
            inputMode="numeric"
            value={pendingQuantity}
            disabled={!pendingProduct}
            onChange={(event) => setPendingQuantity(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.ctrlKey && !event.metaKey) {
                event.preventDefault();
                addPendingLine();
              }
            }}
          />
        </div>
        <Button variant="outline" onClick={addPendingLine} disabled={!pendingProduct}>
          <ListPlus />
          {t("booking.addLine")}
        </Button>
        {action === "kar_unload" && karDetail && (
          <Button variant="outline" onClick={fillEverything}>
            <PackageOpen />
            {t("booking.unloadEverything")}
          </Button>
        )}
      </div>
      <p className="text-xs text-muted-foreground">{t("booking.keyboardHint")}</p>
    </>
  );

  // The booking's details (team/festival, reason, reference, comment), the summary and the confirm button
  // (side column; Kar laden has its own compact bar, karLoadBar).
  const bookingDetails = (
    <>
      {action === "kar_dispatch" && (
        <>
          <NamedSelect
            id="booking-team"
            label={t("booking.teamLabel")}
            value={teamId}
            items={lookups?.teams ?? []}
            emptyLabel={t("booking.noTeam")}
            onChange={setTeamId}
          />
          <NamedSelect
            id="booking-festival"
            label={t("booking.festivalLabel")}
            value={festivalId}
            items={karDetail?.festivals ?? []}
            emptyLabel={t("booking.noFestival")}
            onChange={setFestivalId}
          />
        </>
      )}
      {action === "book_out" && (
        <NamedSelect
          id="booking-reason"
          label={`${t("booking.reasonLabel")} *`}
          value={reasonId}
          items={reasons}
          emptyLabel={t("booking.chooseReason")}
          onChange={setReasonId}
        />
      )}
      {(action === "book_in" || action === "book_out" || action === "kar_load" || action === "kar_dispatch") && (
        <div className="flex flex-col gap-2">
          <Label htmlFor="booking-reference">
            {action === "book_in" ? t("booking.deliveryNoteLabel") : t("booking.referenceLabel")}
          </Label>
          <Input id="booking-reference" value={reference} onChange={(event) => setReference(event.target.value)} />
        </div>
      )}
      <div className="flex flex-col gap-2">
        <Label htmlFor="booking-comment">{t("booking.commentLabel")}</Label>
        <Textarea id="booking-comment" value={comment} onChange={(event) => setComment(event.target.value)} rows={2} />
      </div>

      <BookingSummary action={action} lines={activeLines} detail={karDetail} productsById={productsById} />

      <Button size="lg" onClick={() => void handleSubmit()} disabled={!canSubmit}>
        {tAction("confirm")}
      </Button>
      {missingReason && <p className="text-xs text-muted-foreground">{t("errors.reason_required")}</p>}
      <p className="text-xs text-muted-foreground">{t("booking.confirmHint")}</p>
    </>
  );

  // Kar laden: load from free stock (default) or from another kar in the warehouse. On the
  // kar's own screen it sits in the "Karinhoud" title row, with its label inline.
  const loadSourceSelect = (
    <SourceSelect
      id="booking-from"
      label={t("booking.fromLabel")}
      value={fromKarId}
      kars={kars.filter((kar) => !kar.is_out && kar.kar_id !== karId && kar.total_quantity > 0)}
      onChange={(value) => {
        setFromKarId(value);
        // Another source: the quantities start over; on Kar laden the manual products stay.
        setLines((current) => (action === "kar_load" ? current.map((line) => ({ ...line, quantity: 0 })) : []));
      }}
      inline={showsKarLoadHeader}
    />
  );

  // Kar laden: "Manueel product toevoegen" as a pop-up (the product entry inside); it closes
  // after "Toevoegen" and a toast confirms the product.
  const manualAddDialog = (
    <Dialog
      open={isManualOpen}
      onOpenChange={(open) => {
        setIsManualOpen(open);
        if (open) window.setTimeout(() => searchRef.current?.focus(), 50);
      }}
    >
      <DialogTrigger render={<Button variant="outline" disabled={seasonLocked} />}>
        <ListPlus />
        {t("karLoad.manualAddTitle")}
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t("karLoad.manualAddTitle")}</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          {productEntry}
        </div>
        <DialogFooter>
          <DialogClose render={<Button variant="outline" />}>{t("karLoad.close")}</DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );

  // Kar laden: reference, comment and the confirm button in one row above the table; the
  // "stored under your name" and Ctrl+Enter hints are in the button's tooltip.
  const karLoadBar = (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex w-48 flex-col gap-1.5">
        <Label htmlFor="booking-reference">{t("booking.referenceLabel")}</Label>
        <Input id="booking-reference" value={reference} onChange={(event) => setReference(event.target.value)} />
      </div>
      <div className="flex min-w-48 flex-1 flex-col gap-1.5">
        <Label htmlFor="booking-comment">{t("booking.commentLabel")}</Label>
        <Input id="booking-comment" value={comment} onChange={(event) => setComment(event.target.value)} />
      </div>
      {/* The tooltip sits on a wrapper: a disabled button shows none. */}
      <span title={`${t("booking.confirmHint")} ${t("karLoad.confirmShortcut")}`}>
        <Button onClick={() => void handleSubmit()} disabled={!canSubmit}>
          {tAction("confirm")}
        </Button>
      </span>
    </div>
  );

  // The last booking made on this screen (PDF, view, undo).
  const lastBookingCard = lastBooking && (
    <Card>
      <CardContent className="flex flex-col gap-2 text-sm">
        <span className="font-semibold">{t("booking.lastBooking")}</span>
        <span>
          {lastBooking.doc_number} · {t(`docTypes.${lastBooking.doc_type}`)} ·{" "}
          {t("booking.pieces", { count: lastBooking.total_quantity })}
        </span>
        <div className="flex flex-wrap gap-2">
          {(canSeeBookings || lastBooking.doc_type === "kar_dispatch") && (
            <a
              href={stockMasterBookingPdfUrl(lastBooking.id, locale)}
              target="_blank"
              rel="noreferrer"
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              <FileText />
              {lastBooking.doc_type === "kar_dispatch" ? t("booking.dispatchNote") : t("booking.bookingNote")}
            </a>
          )}
          {canSeeBookings && (
            <Link
              href={`${STOCKMASTER_BASE}/bookings/${lastBooking.id}`}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              {t("booking.viewBooking")}
            </Link>
          )}
          {canUndo && lastBooking.doc_type !== "reversal" && lastBooking.status === "posted" && (
            <Button variant="ghost" size="sm" onClick={() => void undo(lastBooking)}>
              {t("booking.undo")}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="flex flex-col gap-6" onKeyDown={handleKeyDown}>
      {/* Where this screen sits in the warehouse process (not on Uitboeken). */}
      {isProcessFlowAction(action) && <ProcessFlow action={action} permissions={permissions} />}

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          {/* Kar laden: back to the loading overview of every kar. */}
          {action === "kar_load" && (
            <Link
              href={`${STOCKMASTER_BASE}${ACTION_PATHS.kar_load}${seasonId ? `?season=${seasonId}` : ""}`}
              className="mb-1 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="size-4" />
              {t("karLoadOverview.back")}
            </Link>
          )}
          <h1 className="text-2xl font-bold tracking-tight underline">{tAction("title")}</h1>
          <p className="text-muted-foreground">{tAction("description")}</p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {seasonLocked && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{t("errors.season_closed")}</p>}

      {/* Kar laden: the kar as a header on top (refreshed after every booking). */}
      {showsKarLoadHeader && karDetail && <KarLoadHeader detail={karDetail} onClear={() => chooseKar(null)} />}

      {/* Kar laden has no side column: the booking's details sit in a bar above the table, so the
          table gets the full width. */}
      <div className={cn("grid gap-6", !showsKarLoadHeader && "lg:grid-cols-[minmax(0,1fr)_24rem]")}>
        {/* Kar laden: one "Karinhoud" block, framed like the kar header but on a plain background:
            the title row with its buttons, the reference/comment/confirm bar and the table. */}
        <div
          className={cn(
            "flex flex-col gap-6",
            showsKarLoadHeader && "min-w-0 gap-4 rounded-xl border-2 border-primary/40 bg-background px-5 py-4",
          )}
        >
          {showsKarLoadHeader && (
            // Title, with on the right where the products come from, the manual-add pop-up and the
            // buttons that work on the checked rows ("Vul aan" not when loading from another kar).
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">{t("karLoad.karContentsTitle")}</h2>
              <div className="flex flex-wrap items-center gap-2">
                {loadSourceSelect}
                {manualAddDialog}
                {fromKarId === null && (
                  <Button variant="outline" onClick={fillMissing} disabled={selectedIds.size === 0}>
                    {t("booking.fillMissing")}
                  </Button>
                )}
                <Button variant="outline" onClick={removeSelected} disabled={selectedIds.size === 0 || seasonLocked}>
                  <Trash2 />
                  {t("karLoad.removeSelected")}
                </Button>
              </div>
            </div>
          )}
          {/* The kar (kar actions; on Kar laden only until one is chosen,
              the header above shows it then), or the source (Uitboeken). */}
          {isKarAction && (!showsKarLoadHeader || (selectedKar !== null && karDisabled(selectedKar))) && (
            <div className="flex flex-col gap-2">
              {!showsKarLoadHeader && (
                <>
                  <Label htmlFor="booking-kar">{t("booking.karLabel")}</Label>
                  {selectedKar ? (
                    <SelectedKar kar={selectedKar} onClear={() => chooseKar(null)} />
                  ) : (
                    <KarSearch id="booking-kar" kars={kars} onSelect={chooseKar} isDisabled={karDisabled} autoFocus />
                  )}
                </>
              )}
              {selectedKar && karDisabled(selectedKar) && (
                <p className="text-sm text-destructive">
                  {action === "kar_return"
                    ? t("errors.kar_not_out", { p1: selectedKar.kar_nummer })
                    : t("errors.kar_out", { p1: selectedKar.kar_nummer })}
                </p>
              )}
            </div>
          )}

          {action === "kar_load" && !showsKarLoadHeader && loadSourceSelect}
          {action === "book_out" && (
            <SourceSelect
              id="booking-source"
              label={t("booking.fromLabel")}
              value={karId}
              kars={kars.filter((kar) => !kar.is_out && kar.total_quantity > 0)}
              onChange={(value) => {
                setKarId(value);
                setLines([]);
              }}
            />
          )}

          {action === "kar_dispatch" && karDetail && selectedKar && (
            <DispatchContents detail={karDetail} />
          )}

          {/* Kar laden: the reference/comment/confirm bar, then the table of the kar's products. */}
          {/* Kar laden of a kar that's out: what's confirmed is delivered to the festival afterwards. */}
          {showsKarLoadHeader && karDetail?.kar.is_out && (
            <p className="rounded-md border border-orange-500/40 bg-orange-500/10 px-3 py-2 text-sm text-orange-800 dark:text-orange-200">
              {t("karLoad.deliveryNote", { kar: karDetail.kar.kar_nummer })}
            </p>
          )}
          {showsKarLoadHeader && karLoadBar}
          {showsKarLoadHeader && (
            <KarLoadTable
              rows={karRows}
              selected={selectedIds}
              onToggle={toggleRow}
              onToggleAll={(checked) => setSelectedIds(checked ? new Set(karRows.map((row) => row.key)) : new Set())}
              onQuantityChange={(row, quantity) => setRowQuantities(new Map([[row.key, quantity]]))}
              onRemove={(row) => void removeManualRows([row])}
              lineProblem={(row) => {
                // Only a product with something to deliver now can have a problem.
                const total = productTotal(row);
                return row.product && total.quantity > 0 ? lineProblem(total, row.product) : null;
              }}
              placeChanges={(row) => (row.product ? placeChanges(productTotal(row), row.product) : [])}
            />
          )}

          {usesBasket && !showsKarLoadHeader && (!isKarAction || selectedKar) && (
            <Card>
              <CardContent className="flex flex-col gap-4">
                {productEntry}

                {/* Inboeken from Excel: download the template, upload it filled in → basket. */}
                {action === "book_in" && (
                  <div className="flex flex-col gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <a
                        href={stockMasterBookInTemplateUrl()}
                        download
                        className={buttonVariants({
                          variant: "outline",
                          size: "sm",
                        })}
                      >
                        <FileSpreadsheet />
                        {t("booking.importTemplate")}
                      </a>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => importInputRef.current?.click()}
                        disabled={isImporting}
                      >
                        <Upload />
                        {t("booking.importUpload")}
                      </Button>
                      {/* Inboeken from a TagScan scan: opens the "scans waiting" dialog. */}
                      <Button variant="outline" size="sm" onClick={openTagscanBookInDialog}>
                        <ScanLine />
                        {t("booking.scanLoad")}
                      </Button>
                      <input
                        ref={importInputRef}
                        type="file"
                        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        className="hidden"
                        onChange={(event) => {
                          const file = event.target.files?.[0];
                          // Cleared right away so the same file can be uploaded again after fixing it.
                          event.target.value = "";
                          if (file) void importExcel(file);
                        }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground">{t("booking.importHint")}</p>
                    {/* The scan(s) this basket came from; booking marks their lines "loaded". */}
                    {scanFilenames.length > 0 && (
                      <div className="flex w-fit items-center gap-2 rounded-md border bg-muted/50 px-3 py-1 text-sm">
                        <ScanLine className="size-4 text-muted-foreground" />
                        <span>
                          {t("booking.scanFrom", {
                            files: scanFilenames.join(", "),
                          })}
                        </span>
                        <button
                          type="button"
                          onClick={dropScanLink}
                          aria-label={t("booking.scanDrop")}
                          title={t("booking.scanDrop")}
                        >
                          <X className="size-4" />
                        </button>
                      </div>
                    )}
                    {scanProblems.length > 0 && (
                      <div className="rounded-md border border-orange-500/40 bg-orange-500/10 px-3 py-2 text-sm text-orange-700 dark:text-orange-300">
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-semibold">{t("booking.scanErrorsTitle")}</span>
                          <button
                            type="button"
                            onClick={() => setScanProblems([])}
                            aria-label={t("booking.importClose")}
                          >
                            <X className="size-4" />
                          </button>
                        </div>
                        <ul className="mt-1 list-disc pl-5">
                          {scanProblems.map((problem) => (
                            <li key={problem.lineId}>
                              {t("booking.scanErrorRow", {
                                file: problem.filename,
                                row: problem.lineNumber,
                                message: importErrorText(problem.detail),
                              })}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {importErrors.length > 0 && (
                      <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-semibold">{t("booking.importErrorsTitle")}</span>
                          <button
                            type="button"
                            onClick={() => setImportErrors([])}
                            aria-label={t("booking.importClose")}
                          >
                            <X className="size-4" />
                          </button>
                        </div>
                        <ul className="mt-1 list-disc pl-5">
                          {importErrors.map((error) => (
                            <li key={`${error.row_number}-${error.detail}`}>
                              {t("booking.importErrorRow", {
                                row: error.row_number,
                                message: importErrorText(error.detail),
                              })}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                <BasketTable
                  action={action}
                  lines={lines}
                  productsById={productsById}
                  placeChanges={placeChanges}
                  lineProblem={lineProblem}
                  onChange={updateLine}
                  onRemove={removeLine}
                />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Side column: the booking's details and the confirm button (on Kar laden they sit in the bar above the table). */}
        {!showsKarLoadHeader && (
          <div className="flex flex-col gap-4">
            <Card>
              <CardContent className="flex flex-col gap-4">{bookingDetails}</CardContent>
            </Card>
            {lastBookingCard}
          </div>
        )}
      </div>

      {/* Kar laden: the last booking at the bottom of the page. */}
      {showsKarLoadHeader && lastBookingCard && <div className="lg:w-96">{lastBookingCard}</div>}
    </div>
  );
}

/** Kar laden: one line per product, summing its rows (kar need + Manueel). */
function totalPerProduct(lines: BasketLine[]): BasketLine[] {
  const totals = new Map<number, number>();
  for (const line of lines) totals.set(line.productId, (totals.get(line.productId) ?? 0) + line.quantity);
  return [...totals].map(([productId, quantity]) => ({ productId, quantity }));
}

/** "?prefill=12:5,13:2" (from Te bestellen) as basket lines. */
function parsePrefill(value: string | null): BasketLine[] {
  if (!value) return [];
  return value
    .split(",")
    .map((part) => part.split(":").map(Number))
    .filter(([productId, quantity]) => productId > 0 && quantity > 0)
    .map(([productId, quantity]) => ({ productId, quantity }));
}

interface SourceSelectProps {
  id: string;
  label: string;
  value: number | null;
  kars: StockMasterKarSummary[];
  onChange: (karId: number | null) => void;
  /** Label left of the dropdown instead of above it. */
  inline?: boolean;
}

/** "Van": free stock (default) or a kar standing in the warehouse. */
function SourceSelect({ id, label, value, kars, onChange, inline = false }: SourceSelectProps) {
  const t = useTranslations("stockMaster");
  return (
    <div className={cn("flex max-w-sm gap-2", inline ? "items-center" : "flex-col")}>
      <Label htmlFor={id}>{label}</Label>
      <Select
        value={value === null ? FREE_SOURCE : String(value)}
        onValueChange={(next) => onChange(next && next !== FREE_SOURCE ? Number(next) : null)}
      >
        <SelectTrigger id={id}>
          <SelectValue>
            {(current: string | null) =>
              current === FREE_SOURCE || !current
                ? t("common.freeStock")
                : t("booking.fromKar", { kar: kars.find((kar) => String(kar.kar_id) === current)?.kar_nummer ?? "" })
            }
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={FREE_SOURCE}>{t("common.freeStock")}</SelectItem>
          {kars.map((kar) => (
            <SelectItem key={kar.kar_id} value={String(kar.kar_id)}>
              {t("booking.fromKar", { kar: kar.kar_nummer })}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

interface NamedSelectProps {
  id: string;
  label: string;
  value: number | null;
  items: { id: number; name: string }[];
  emptyLabel: string;
  onChange: (value: number | null) => void;
}

/** A dropdown of {id, name} items with an "empty" choice. */
export function NamedSelect({ id, label, value, items, emptyLabel, onChange }: NamedSelectProps) {
  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Select
        value={value === null ? NO_SELECTION : String(value)}
        onValueChange={(next) => onChange(next && next !== NO_SELECTION ? Number(next) : null)}
      >
        <SelectTrigger id={id} className="w-full">
          <SelectValue>
            {(current: string | null) => items.find((item) => String(item.id) === current)?.name ?? emptyLabel}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NO_SELECTION}>{emptyLabel}</SelectItem>
          {items.map((item) => (
            <SelectItem key={item.id} value={String(item.id)}>
              {item.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

interface BasketTableProps {
  action: StockMasterAction;
  lines: BasketLine[];
  productsById: Map<number, StockMasterProductStock>;
  placeChanges: (line: BasketLine, product: StockMasterProductStock) => PlaceChange[];
  lineProblem: (line: BasketLine, product: StockMasterProductStock) => string | null;
  onChange: (productId: number, changes: Partial<BasketLine>) => void;
  onRemove: (productId: number) => void;
}

/** The basket: one row per product, with before → after and any problem. */
function BasketTable({ action, lines, productsById, placeChanges, lineProblem, onChange, onRemove }: BasketTableProps) {
  const t = useTranslations("stockMaster");
  const isReturn = action === "kar_return";

  if (lines.length === 0) {
    return <p className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">{t("booking.emptyBasket")}</p>;
  }

  return (
    <div className="rounded-md border [&>div]:max-h-[55vh] [&>div]:overflow-y-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="sticky top-0 z-20 w-14 bg-background">
              <span className="sr-only">{t("karLoad.picture")}</span>
            </TableHead>
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("booking.productLabel")}</TableHead>
            {isReturn && (
              <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("booking.dispatched")}</TableHead>
            )}
            <TableHead className="sticky top-0 z-20 w-28 bg-background font-bold underline">
              {isReturn ? t("booking.returned") : t("booking.quantityLabel")}
            </TableHead>
            {isReturn && (
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("booking.destination")}</TableHead>
            )}
            <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("booking.preview")}</TableHead>
            <TableHead className="sticky top-0 right-0 z-30 w-12 bg-background text-right font-bold underline">
              <span className="sr-only">{t("common.actions")}</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {lines.map((line) => {
            const product = productsById.get(line.productId);
            if (!product) return null;
            const problem = lineProblem(line, product);
            const notReturned = isReturn ? (line.dispatched ?? 0) - line.quantity : 0;
            return (
              <TableRow key={line.productId} className="group">
                {/* The product's picture (or a placeholder), webshop-style. */}
                <TableCell>
                  <ProductThumb productId={product.product_id} name={product.name} product={product} />
                </TableCell>
                <TableCell>
                  <div className="font-medium">{product.name}</div>
                  <div className="text-xs text-muted-foreground">{product.bin_label ?? t("common.noBin")}</div>
                  {problem && <div className="text-xs font-medium text-destructive">{problem}</div>}
                  {isReturn && notReturned > 0 && (
                    <div className="text-xs text-orange-700 dark:text-orange-300">
                      {product.is_consumable
                        ? t("booking.consumed", { count: notReturned })
                        : t("booking.missing", { count: notReturned })}
                    </div>
                  )}
                </TableCell>
                {isReturn && <TableCell className="text-right tabular-nums">{line.dispatched ?? 0}</TableCell>}
                <TableCell>
                  <Input
                    type="number"
                    min={isReturn ? 0 : 1}
                    step={1}
                    inputMode="numeric"
                    aria-label={t("booking.quantityLabel")}
                    className={cn("w-24", problem && "border-destructive")}
                    value={line.quantity}
                    onChange={(event) =>
                      onChange(line.productId, { quantity: Math.max(0, Number.parseInt(event.target.value, 10) || 0) })
                    }
                  />
                </TableCell>
                {isReturn && (
                  <TableCell>
                    <Select
                      value={line.destination ?? "kar"}
                      onValueChange={(value) => onChange(line.productId, { destination: value === "free" ? "free" : "kar" })}
                    >
                      <SelectTrigger className="w-40" aria-label={t("booking.destination")}>
                        <SelectValue>
                          {(value: string | null) => (value === "free" ? t("common.freeStock") : t("booking.backInKar"))}
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="kar">{t("booking.backInKar")}</SelectItem>
                        <SelectItem value="free">{t("common.freeStock")}</SelectItem>
                      </SelectContent>
                    </Select>
                  </TableCell>
                )}
                <TableCell className="text-sm tabular-nums">
                  {placeChanges(line, product).map((change) => (
                    <div key={change.label} className={cn(change.after < 0 && "text-destructive")}>
                      <span className="text-muted-foreground">{change.label}</span> {change.before} → <strong>{change.after}</strong>
                    </div>
                  ))}
                </TableCell>
                <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                  <Button variant="ghost" size="icon-sm" onClick={() => onRemove(line.productId)} aria-label={t("booking.removeLine")}>
                    <Trash2 />
                  </Button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

/** What leaves with the kar on "Kar vertrekt" (read-only). */
function DispatchContents({ detail }: { detail: StockMasterKarDetail }) {
  const t = useTranslations("stockMaster");
  const contents = detail.lines.filter((line) => line.in_kar > 0);
  const missing = detail.lines.filter((line) => line.missing > 0);
  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <h2 className="font-semibold">{t("booking.leavesWithKar")}</h2>
        {contents.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("booking.karEmpty")}</p>
        ) : (
          <ul className="divide-y text-sm">
            {contents.map((line) => (
              <li key={line.product_id} className="flex justify-between py-1.5">
                <span>{line.name}</span>
                <span className="font-semibold tabular-nums">{line.in_kar}</span>
              </li>
            ))}
          </ul>
        )}
        {missing.length > 0 && (
          <p className="rounded-md bg-orange-50 px-3 py-2 text-sm text-orange-800 dark:bg-orange-500/10 dark:text-orange-200">
            {t("booking.stillMissing", { count: missing.reduce((sum, line) => sum + line.missing, 0) })}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

/** "3 producten · 12 stuks" above the confirm button, followed by each product (picture, name, quantity). */
function BookingSummary({
  action,
  lines,
  detail,
  productsById,
}: {
  action: StockMasterAction;
  lines: BasketLine[];
  detail: StockMasterKarDetail | null;
  productsById: Map<number, StockMasterProductStock>;
}) {
  const t = useTranslations("stockMaster.booking");

  // "Kar vertrekt" books the kar's whole contents, so list those; otherwise the basket lines with a quantity.
  const rows =
    action === "kar_dispatch"
      ? (detail?.lines ?? [])
          .filter((line) => line.in_kar > 0)
          .map((line) => ({
            id: line.product_id,
            name: line.name,
            quantity: line.in_kar,
          }))
      : lines
          .filter((line) => line.quantity > 0)
          .map((line) => ({
            id: line.productId,
            name: productsById.get(line.productId)?.name ?? "",
            quantity: line.quantity,
          }));

  return (
    <div className="flex flex-col gap-1">
      <p className="text-sm">
        {t("summary", {
          products: rows.length,
          pieces: rows.reduce((sum, row) => sum + row.quantity, 0),
        })}
      </p>
      {/* One row per product, webshop-style with a small picture; capped in height so the confirm button
          stays in view on long baskets. */}
      {rows.length > 0 && (
        <ul className="max-h-72 divide-y overflow-y-auto text-sm">
          {rows.map((row) => (
            <li key={row.id} className="flex items-center gap-3 py-1.5">
              {/* The picture, or a placeholder icon so every row stays aligned. */}
              <ProductThumb productId={row.id} name={row.name} product={productsById.get(row.id)} />
              <span className="min-w-0 flex-1 truncate" title={row.name}>
                {row.name}
              </span>
              <span className="font-semibold tabular-nums">{row.quantity}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
