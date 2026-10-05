"use client";

// StockMaster's "Benodigdheden": what each team needs in which kar, per
// season. Pick a team, then one of its kars, and edit the product list with
// the same basket-style input as the booking panel (search, Enter,
// quantity, Enter). "Kopieer van vorig seizoen" offers last season's list of
// the same kar line by line (only adds/updates, never removes). Saving
// stores the list under the logged-in user. These needs pre-fill "Kar
// laden", show as loading progress on the kar cards and feed "Te bestellen".

import { useEffect, useMemo, useRef, useState } from "react";
import { Copy, FileText, Trash2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";
import {
  getStockMasterPreviousRequirements,
  getStockMasterRequirements,
  getStockMasterStock,
  listStockMasterKars,
  saveStockMasterRequirements,
  stockMasterLoadListPdfUrl,
} from "@/lib/api";
import type {
  Season,
  StockMasterKarSummary,
  StockMasterMyPermissions,
  StockMasterPreviousRequirements,
  StockMasterProductStock,
  StockMasterRequirement,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ProductSearch } from "@/components/module-4/stock-pickers";
import { StockMasterSeasonSelect, useStockMasterSeasonId } from "@/components/module-4/stockmaster-season-select";
import { hasRight, stockErrorMessage } from "@/components/module-4/stockmaster-common";

interface RequirementsEditorProps {
  seasons: Season[];
  permissions: StockMasterMyPermissions;
}

/** One line being edited. */
interface EditLine {
  productId: number;
  name: string;
  binLabel: string | null;
  quantity: number;
  comment: string;
  inKar: number;
  /** Already stored (so changing/removing it needs edit/delete rights). */
  stored: boolean;
}

const NO_TEAM = "none";

export function RequirementsEditor({ seasons, permissions }: RequirementsEditorProps) {
  const t = useTranslations("stockMaster");
  const tReq = useTranslations("stockMaster.requirements");
  const locale = useLocale();
  const searchParams = useSearchParams();
  const seasonId = useStockMasterSeasonId(seasons);
  const season = seasons.find((item) => item.id === seasonId) ?? null;

  const canCreate = hasRight(permissions, "requirements", "create");
  const canEdit = hasRight(permissions, "requirements", "edit");
  const canDelete = hasRight(permissions, "requirements", "delete");
  const seasonLocked =
    season !== null && !season.periode_open && !permissions.editable_screen_keys.includes("stockmaster.closedseason");

  const [kars, setKars] = useState<StockMasterKarSummary[]>([]);
  const [stock, setStock] = useState<StockMasterProductStock[]>([]);
  const [teamName, setTeamName] = useState<string | null>(null);
  const [karId, setKarId] = useState<number | null>(() => Number(searchParams.get("kar")) || null);
  // The list being edited and last season's list, each stored with the
  // "season:kar" they belong to, so a list never shows (or gets saved) under
  // another kar while the next one is loading.
  const [edit, setEdit] = useState<{ key: string; lines: EditLine[] } | null>(null);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [previousState, setPreviousState] = useState<{ key: string; data: StockMasterPreviousRequirements } | null>(null);
  const [pickedPrevious, setPickedPrevious] = useState<Set<number>>(new Set());
  const [pendingProduct, setPendingProduct] = useState<StockMasterProductStock | null>(null);
  const [pendingQuantity, setPendingQuantity] = useState("1");
  const searchRef = useRef<HTMLInputElement>(null);
  const quantityRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getStockMasterStock()
      .then(setStock)
      .catch(() => toast.error(t("errors.loadFailed")));
  }, [t]);

  useEffect(() => {
    listStockMasterKars(seasonId)
      .then((result) => {
        setKars(result);
        // A kar passed in the URL also picks its team.
        const fromUrl = result.find((kar) => kar.kar_id === karId);
        if (fromUrl) setTeamName(fromUrl.team_name ?? NO_TEAM);
      })
      .catch(() => toast.error(t("errors.loadFailed")));
    // Only on a season change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seasonId, t]);

  const teams = useMemo(() => {
    const names = new Set(kars.map((kar) => kar.team_name ?? NO_TEAM));
    return [...names].sort((a, b) => (a === NO_TEAM ? 1 : b === NO_TEAM ? -1 : a.localeCompare(b)));
  }, [kars]);
  const teamKars = kars.filter((kar) => (kar.team_name ?? NO_TEAM) === teamName);
  const selectedKar = kars.find((kar) => kar.kar_id === karId) ?? null;
  const currentKey = seasonId !== null && karId !== null ? `${seasonId}:${karId}` : null;
  const lines = edit !== null && edit.key === currentKey ? edit.lines : null;
  const previous = previousState !== null && previousState.key === currentKey ? previousState.data : null;

  // Load the chosen kar's list (and last season's, for the copy panel).
  useEffect(() => {
    if (seasonId === null || karId === null) return;
    const key = `${seasonId}:${karId}`;
    getStockMasterRequirements(seasonId, karId)
      .then((rows) => {
        setEdit({ key, lines: rows.map(toEditLine) });
        setIsDirty(false);
      })
      .catch((error) => toast.error(stockErrorMessage(t, error)));
    getStockMasterPreviousRequirements(seasonId, karId)
      .then((result) => {
        setPreviousState({ key, data: result });
        setPickedPrevious(new Set(result.lines.map((line) => line.product_id)));
      })
      .catch(() => undefined);
  }, [seasonId, karId, t]);

  function change(updater: (current: EditLine[]) => EditLine[]) {
    setEdit((current) => (current !== null && current.key === currentKey ? { key: current.key, lines: updater(current.lines) } : current));
    setIsDirty(true);
  }

  function addPending() {
    if (!pendingProduct) return;
    const quantity = Number.parseInt(pendingQuantity, 10);
    if (!Number.isFinite(quantity) || quantity < 1) {
      toast.error(t("booking.quantityTooLow"));
      return;
    }
    const product = pendingProduct;
    change((current) => {
      const existing = current.find((line) => line.productId === product.product_id);
      if (existing) {
        return current.map((line) => (line === existing ? { ...line, quantity: line.quantity + quantity } : line));
      }
      const inKar = product.kars.find((kar) => kar.kar_id === karId)?.quantity ?? 0;
      return [
        ...current,
        { productId: product.product_id, name: product.name, binLabel: product.bin_label, quantity, comment: "", inKar, stored: false },
      ];
    });
    setPendingProduct(null);
    setPendingQuantity("1");
    window.setTimeout(() => searchRef.current?.focus(), 0);
  }

  /** Copy the ticked lines of last season (adds or updates, never removes). */
  function copyPrevious() {
    if (!previous) return;
    change((current) => {
      const next = [...current];
      for (const line of previous.lines) {
        if (!pickedPrevious.has(line.product_id)) continue;
        const existing = next.findIndex((item) => item.productId === line.product_id);
        if (existing >= 0) {
          next[existing] = { ...next[existing], quantity: line.quantity };
        } else {
          const product = stock.find((item) => item.product_id === line.product_id);
          next.push({
            productId: line.product_id,
            name: line.product_name,
            binLabel: product?.bin_label ?? null,
            quantity: line.quantity,
            comment: "",
            inKar: product?.kars.find((kar) => kar.kar_id === karId)?.quantity ?? 0,
            stored: false,
          });
        }
      }
      return next;
    });
    toast.success(tReq("copied"));
  }

  async function save() {
    if (seasonId === null || karId === null || !lines) return;
    setIsSaving(true);
    try {
      const rows = await saveStockMasterRequirements(
        seasonId,
        karId,
        lines.map((line) => ({ product_id: line.productId, quantity: line.quantity, comment: line.comment.trim() || null })),
      );
      setEdit({ key: `${seasonId}:${karId}`, lines: rows.map(toEditLine) });
      setIsDirty(false);
      toast.success(tReq("saved"));
    } catch (error) {
      toast.error(stockErrorMessage(t, error));
    } finally {
      setIsSaving(false);
    }
  }

  const readOnly = seasonLocked || (!canCreate && !canEdit && !canDelete);
  const invalid = (lines ?? []).some((line) => !Number.isInteger(line.quantity) || line.quantity < 1);
  const total = (lines ?? []).reduce((sum, line) => sum + line.quantity, 0);

  return (
    <div
      className="flex flex-col gap-6"
      onKeyDown={(event) => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
          event.preventDefault();
          if (isDirty && !invalid && !readOnly) void save();
        }
      }}
    >
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{tReq("title")}</h1>
          <p className="text-muted-foreground">{tReq("description")}</p>
        </div>
        <StockMasterSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {seasonLocked && <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{t("errors.season_closed")}</p>}

      <div className="flex flex-wrap items-end gap-4">
        <div className="flex w-64 flex-col gap-2">
          <Label htmlFor="req-team">{t("common.team")}</Label>
          <Select
            value={teamName ?? ""}
            onValueChange={(value) => {
              setTeamName(value || null);
              // A team with just one kar opens that kar's list straight away.
              const karsOfTeam = kars.filter((kar) => (kar.team_name ?? NO_TEAM) === value);
              setKarId(karsOfTeam.length === 1 ? karsOfTeam[0].kar_id : null);
            }}
          >
            <SelectTrigger id="req-team" className="w-full">
              <SelectValue>
                {(value: string | null) => (!value ? tReq("chooseTeam") : value === NO_TEAM ? t("common.noTeam") : value)}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              {teams.map((name) => (
                <SelectItem key={name} value={name}>
                  {name === NO_TEAM ? t("common.noTeam") : name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {teamName !== null && (
          <div className="flex flex-col gap-2">
            <Label>{tReq("chooseKar")}</Label>
            <div className="flex flex-wrap gap-2">
              {teamKars.map((kar) => (
                <Button
                  key={kar.kar_id}
                  variant={kar.kar_id === karId ? "default" : "outline"}
                  onClick={() => {
                    if (isDirty && !window.confirm(tReq("discardChanges"))) return;
                    setKarId(kar.kar_id);
                  }}
                >
                  {kar.kar_nummer}
                  {kar.required_total > 0 && (
                    <span className="text-xs opacity-75">
                      {kar.loaded_toward_required}/{kar.required_total}
                    </span>
                  )}
                </Button>
              ))}
            </div>
          </div>
        )}
      </div>

      {selectedKar && lines !== null && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="flex flex-col gap-4">
            {!readOnly && canCreate && (
              <div className="flex flex-wrap items-end gap-3">
                <div className="flex min-w-64 flex-1 flex-col gap-2">
                  <Label htmlFor="req-product">{t("booking.productLabel")}</Label>
                  {pendingProduct ? (
                    <div className="flex h-8 items-center gap-2 rounded-md border bg-muted/40 px-3 text-sm">
                      <span className="font-medium">{pendingProduct.name}</span>
                      <button type="button" className="ml-auto text-xs text-muted-foreground underline" onClick={() => setPendingProduct(null)}>
                        {t("booking.otherProduct")}
                      </button>
                    </div>
                  ) : (
                    <ProductSearch
                      id="req-product"
                      ref={searchRef}
                      products={stock}
                      onSelect={(product) => {
                        setPendingProduct(product);
                        window.setTimeout(() => quantityRef.current?.select(), 0);
                      }}
                    />
                  )}
                </div>
                <div className="flex w-28 flex-col gap-2">
                  <Label htmlFor="req-quantity">{t("booking.quantityLabel")}</Label>
                  <Input
                    id="req-quantity"
                    ref={quantityRef}
                    type="number"
                    min={1}
                    step={1}
                    inputMode="numeric"
                    disabled={!pendingProduct}
                    value={pendingQuantity}
                    onChange={(event) => setPendingQuantity(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" && !event.ctrlKey && !event.metaKey) {
                        event.preventDefault();
                        addPending();
                      }
                    }}
                  />
                </div>
                <Button variant="outline" onClick={addPending} disabled={!pendingProduct}>
                  {t("booking.addLine")}
                </Button>
              </div>
            )}

            {lines.length === 0 ? (
              <p className="rounded-md border border-dashed px-4 py-6 text-center text-sm text-muted-foreground">{tReq("empty")}</p>
            ) : (
              <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.product")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.bin")}</TableHead>
                      <TableHead className="sticky top-0 z-20 w-28 bg-background font-bold underline">{tReq("quantity")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{tReq("comment")}</TableHead>
                      <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.inKar")}</TableHead>
                      <TableHead className="sticky top-0 right-0 z-30 w-12 bg-background text-right font-bold underline">
                        <span className="sr-only">{t("common.actions")}</span>
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lines.map((line) => {
                      const editable = !readOnly && (line.stored ? canEdit : canCreate);
                      return (
                        <TableRow key={line.productId} className="group">
                          <TableCell className="font-medium">{line.name}</TableCell>
                          <TableCell className="text-muted-foreground">{line.binLabel ?? t("common.noBin")}</TableCell>
                          <TableCell>
                            <Input
                              type="number"
                              min={1}
                              step={1}
                              inputMode="numeric"
                              aria-label={tReq("quantity")}
                              className="w-24"
                              disabled={!editable}
                              value={line.quantity}
                              onChange={(event) =>
                                change((current) =>
                                  current.map((item) =>
                                    item.productId === line.productId
                                      ? { ...item, quantity: Number.parseInt(event.target.value, 10) || 0 }
                                      : item,
                                  ),
                                )
                              }
                            />
                          </TableCell>
                          <TableCell>
                            <Input
                              aria-label={tReq("comment")}
                              disabled={!editable}
                              value={line.comment}
                              onChange={(event) =>
                                change((current) =>
                                  current.map((item) =>
                                    item.productId === line.productId ? { ...item, comment: event.target.value } : item,
                                  ),
                                )
                              }
                            />
                          </TableCell>
                          <TableCell
                            className={cn(
                              "text-right tabular-nums",
                              line.inKar >= line.quantity ? "text-green-700 dark:text-green-400" : "text-orange-700 dark:text-orange-300",
                            )}
                          >
                            {line.inKar}
                          </TableCell>
                          <TableCell className="sticky right-0 z-10 bg-background text-right group-hover:bg-muted/50">
                            {!readOnly && (line.stored ? canDelete : true) && (
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                aria-label={t("booking.removeLine")}
                                onClick={() => change((current) => current.filter((item) => item.productId !== line.productId))}
                              >
                                <Trash2 />
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
          </div>

          <div className="flex flex-col gap-4">
            <Card>
              <CardContent className="flex flex-col gap-3">
                <p className="text-sm">{t("booking.summary", { products: lines.length, pieces: total })}</p>
                {!readOnly && (
                  <Button size="lg" onClick={() => void save()} disabled={!isDirty || invalid || isSaving}>
                    {tReq("save")}
                  </Button>
                )}
                {isDirty && <p className="text-xs text-orange-700 dark:text-orange-300">{tReq("unsaved")}</p>}
                {seasonId !== null && (
                  <a
                    href={stockMasterLoadListPdfUrl(selectedKar.kar_id, seasonId, locale)}
                    target="_blank"
                    rel="noreferrer"
                    className={buttonVariants({ variant: "outline" })}
                  >
                    <FileText />
                    {t("kars.loadList")}
                  </a>
                )}
              </CardContent>
            </Card>

            {!readOnly && previous && previous.lines.length > 0 && (
              <Card>
                <CardContent className="flex flex-col gap-3 text-sm">
                  <span className="font-semibold">{tReq("previousTitle", { season: previous.season_name ?? "" })}</span>
                  <div className="flex items-center gap-2">
                    <Checkbox
                      id="req-previous-all"
                      checked={pickedPrevious.size === previous.lines.length}
                      onCheckedChange={(checked) =>
                        setPickedPrevious(checked === true ? new Set(previous.lines.map((line) => line.product_id)) : new Set())
                      }
                    />
                    <Label htmlFor="req-previous-all">{tReq("selectAll")}</Label>
                  </div>
                  <ul className="flex max-h-64 flex-col gap-1 overflow-y-auto">
                    {previous.lines.map((line) => (
                      <li key={line.product_id} className="flex items-center gap-2">
                        <Checkbox
                          id={`req-previous-${line.product_id}`}
                          checked={pickedPrevious.has(line.product_id)}
                          onCheckedChange={(checked) =>
                            setPickedPrevious((current) => {
                              const next = new Set(current);
                              if (checked === true) next.add(line.product_id);
                              else next.delete(line.product_id);
                              return next;
                            })
                          }
                        />
                        <Label htmlFor={`req-previous-${line.product_id}`} className="flex-1 font-normal">
                          {line.product_name}
                        </Label>
                        <span className="tabular-nums">{line.quantity}</span>
                        {line.current_quantity !== null && (
                          <span className="text-xs text-muted-foreground">({tReq("now", { count: line.current_quantity })})</span>
                        )}
                      </li>
                    ))}
                  </ul>
                  <Button variant="outline" onClick={copyPrevious} disabled={pickedPrevious.size === 0}>
                    <Copy />
                    {tReq("copy")}
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** A stored need as an editable line. */
function toEditLine(row: StockMasterRequirement): EditLine {
  return {
    productId: row.product_id,
    name: row.product_name,
    binLabel: row.bin_label,
    quantity: row.quantity,
    comment: row.comment ?? "",
    inKar: row.in_kar,
    stored: true,
  };
}
