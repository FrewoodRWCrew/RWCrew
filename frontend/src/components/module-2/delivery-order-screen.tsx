"use client";

// KarTracker's "Leveringsvolgorde" screen: the order of the delivery tour
// across the ground. Left: the tour itself, numbered 1..n, put in order by
// drag and drop. Right: the active delivery locations that aren't in the tour
// yet (by name, searchable). A location moves between both with its arrow
// button or by dragging it across. Nothing is stored until "Save": the
// backend then gives the left-hand list (the tour) position 1..n (terrein_positie)
// and takes every other active location out of the tour.

import { useEffect, useMemo, useRef, useState, type KeyboardEventHandler, type ReactNode } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  type UniqueIdentifier,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ArrowLeft, ArrowRight, GripVertical, Map as MapIcon, Search } from "lucide-react";
import { ApiError, karTrackerGroundplanImageUrl, saveDeliveryOrder } from "@/lib/api";
import type { KarTrackerDeliveryOrderLocation, KarTrackerGroundplan } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { DeliveryOrderMap } from "@/components/module-2/delivery-order-map";
import type { GroundplanOverlay } from "@/components/module-2/kar-map-leaflet";

// The two drop areas; every other drag id is a location id.
const POOL = "pool";
const TOUR = "tour";
type Container = typeof POOL | typeof TOUR;

interface DeliveryOrderScreenProps {
  initialLocations: KarTrackerDeliveryOrderLocation[];
  canEdit: boolean;
  groundplans: KarTrackerGroundplan[];
}

// The ids of the locations already in the tour, in tour order.
function tourFrom(locations: KarTrackerDeliveryOrderLocation[]): number[] {
  return locations
    .filter((location) => location.terrein_positie !== null)
    .sort((a, b) => (a.terrein_positie ?? 0) - (b.terrein_positie ?? 0))
    .map((location) => location.id);
}

export function DeliveryOrderScreen({ initialLocations, canEdit, groundplans }: DeliveryOrderScreenProps) {
  const t = useTranslations("karTracker.deliveryOrder");
  const [locations, setLocations] = useState(initialLocations);
  // What was last saved, to know whether there are unsaved changes.
  const [savedTour, setSavedTour] = useState(() => tourFrom(initialLocations));
  const [tour, setTour] = useState(savedTour);
  const [search, setSearch] = useState("");
  const [activeId, setActiveId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isMapOpen, setIsMapOpen] = useState(false);
  // The tour as it was when a drag started, so Escape can put it back.
  const tourBeforeDrag = useRef<number[] | null>(null);

  // One Leaflet ImageOverlay per ground plan, placed by its own corners (same as Plan a kar).
  const groundplanOverlays = useMemo<GroundplanOverlay[]>(
    () =>
      groundplans.map((groundplan) => ({
        key: groundplan.id,
        url: karTrackerGroundplanImageUrl(groundplan.id, groundplan.updated_at),
        bounds: [
          [groundplan.sw_latitude, groundplan.sw_longitude],
          [groundplan.ne_latitude, groundplan.ne_longitude],
        ],
      })),
    [groundplans],
  );

  const locationsById = useMemo(() => new Map(locations.map((location) => [location.id, location])), [locations]);
  const tourIds = useMemo(() => new Set(tour), [tour]);
  const isDirty = tour.length !== savedTour.length || tour.some((id, index) => id !== savedTour[index]);
  // Locations whose terreinpositie Save will change: a different (or a first)
  // number in the tour, or a saved number that will be cleared.
  const changedCount =
    tour.filter((id, index) => locationsById.get(id)?.terrein_positie !== index + 1).length +
    locations.filter((location) => !tourIds.has(location.id) && location.terrein_positie !== null).length;

  // Left list: everything not in the tour, by name, filtered by the search box.
  const pool = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return locations
      .filter((location) => !tourIds.has(location.id))
      .filter(
        (location) =>
          !needle ||
          [location.description ?? "", location.name, location.zone_name].some((text) =>
            text.toLowerCase().includes(needle),
          ),
      )
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [locations, tourIds, search]);
  const poolTotal = locations.length - tour.length;

  // Warn before leaving the page with an unsaved tour.
  useEffect(() => {
    if (!isDirty) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isDirty]);

  // A small move is needed before a drag starts, so the arrow buttons stay clickable.
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  // Which list a drag id (a location or one of the two drop areas) belongs to.
  function containerOf(id: UniqueIdentifier): Container {
    return id === TOUR || tourIds.has(Number(id)) ? TOUR : POOL;
  }

  function handleDragStart({ active }: DragStartEvent) {
    setActiveId(Number(active.id));
    tourBeforeDrag.current = tour;
  }

  // Crossing from one list to the other moves the location right away, so
  // the tour opens a gap where it will land.
  function handleDragOver({ active, over }: DragOverEvent) {
    if (!over) return;
    const from = containerOf(active.id);
    const to = containerOf(over.id);
    if (from === to) return;

    const locationId = Number(active.id);
    if (to === TOUR) {
      setTour((current) => {
        const overIndex = over.id === TOUR ? current.length : current.indexOf(Number(over.id));
        const next = [...current];
        next.splice(overIndex < 0 ? current.length : overIndex, 0, locationId);
        return next;
      });
    } else {
      setTour((current) => current.filter((id) => id !== locationId));
    }
  }

  // Dropped inside the tour: put it at the spot it was dropped on.
  function handleDragEnd({ active, over }: DragEndEvent) {
    setActiveId(null);
    tourBeforeDrag.current = null;
    if (!over || active.id === over.id) return;
    if (containerOf(active.id) === TOUR && containerOf(over.id) === TOUR && over.id !== TOUR) {
      setTour((current) =>
        arrayMove(current, current.indexOf(Number(active.id)), current.indexOf(Number(over.id))),
      );
    }
  }

  function handleDragCancel() {
    setActiveId(null);
    if (tourBeforeDrag.current) setTour(tourBeforeDrag.current);
    tourBeforeDrag.current = null;
  }

  function addToTour(locationIds: number[]) {
    setTour((current) => [...current, ...locationIds.filter((id) => !current.includes(id))]);
  }

  function removeFromTour(locationId: number) {
    setTour((current) => current.filter((id) => id !== locationId));
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      const saved = await saveDeliveryOrder(tour);
      // The backend's answer is the truth (also picks up others' changes to the location list).
      const savedOrder = tourFrom(saved);
      setLocations(saved);
      setSavedTour(savedOrder);
      setTour(savedOrder);
      toast.success(t("saveSuccess"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveError"));
    } finally {
      setIsSaving(false);
    }
  }

  const activeLocation = activeId !== null ? locationsById.get(activeId) : undefined;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      {/* Save bar (only active once the tour differs from what is saved), and the
          "Kaart" button on the right, above the tour column. */}
      <div className="flex flex-wrap items-center gap-3">
        {canEdit && (
          <>
            <Button onClick={handleSave} disabled={!isDirty || isSaving}>
              {isSaving ? t("saving") : t("save")}
            </Button>
            <Button variant="outline" onClick={() => setTour(savedTour)} disabled={!isDirty || isSaving}>
              {t("undo")}
            </Button>
            {isDirty && (
              <span className="text-sm text-amber-600 dark:text-amber-400">
                {t("unsaved")} · {t("changedCount", { count: changedCount })}
              </span>
            )}
          </>
        )}
        <Button variant="outline" className="ml-auto" onClick={() => setIsMapOpen(true)}>
          <MapIcon className="size-4" />
          {t("mapButton")}
        </Button>
      </div>

      {/* The map of the tour as it is on screen now (unsaved changes included). */}
      <Dialog open={isMapOpen} onOpenChange={setIsMapOpen}>
        <DialogContent className="flex h-[85vh] flex-col sm:max-w-[90vw]">
          <DialogHeader>
            <DialogTitle className="font-bold underline">{t("mapTitle")}</DialogTitle>
            <DialogDescription>{t("mapDescription")}</DialogDescription>
          </DialogHeader>
          <DeliveryOrderMap
            tour={tour.flatMap((id) => locationsById.get(id) ?? [])}
            outside={locations.filter((location) => !tourIds.has(location.id))}
            groundplanOverlays={groundplanOverlays}
          />
        </DialogContent>
      </Dialog>

      {/* A fixed id keeps dnd-kit's generated aria ids the same on server and client (no hydration mismatch). */}
      <DndContext
        id="delivery-order"
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
        onDragCancel={handleDragCancel}
      >
        <div className="grid gap-4 md:grid-cols-2">
          {/* Left: the tour, in delivery order. */}
          <ListColumn
            id={TOUR}
            title={t("tourTitle")}
            count={tour.length}
            toolbar={
              <div className="text-sm text-muted-foreground">
                <p>{canEdit ? t("tourHint") : t("readOnly")}</p>
                <p className="text-xs">{t("legend")}</p>
              </div>
            }
            isEmpty={tour.length === 0}
            emptyText={t("tourEmpty")}
          >
            <SortableContext items={tour} strategy={verticalListSortingStrategy}>
              {tour.map((locationId, index) => {
                const location = locationsById.get(locationId);
                if (!location) return null;
                return (
                  <LocationRow
                    key={location.id}
                    location={location}
                    position={index + 1}
                    disabled={!canEdit}
                    action={
                      canEdit && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeFromTour(location.id)}
                          aria-label={t("removeFromTour")}
                          title={t("removeFromTour")}
                        >
                          <ArrowRight className="size-4" />
                        </Button>
                      )
                    }
                  />
                );
              })}
            </SortableContext>
          </ListColumn>

          {/* Right: not in the tour yet. */}
          <ListColumn
            id={POOL}
            title={t("poolTitle")}
            count={poolTotal}
            toolbar={
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder={t("searchPlaceholder")}
                    className="pl-8"
                  />
                </div>
                {canEdit && (
                  <Button
                    variant="outline"
                    onClick={() => addToTour(pool.map((location) => location.id))}
                    disabled={pool.length === 0}
                  >
                    {t("addAllShown")}
                  </Button>
                )}
              </div>
            }
            isEmpty={pool.length === 0}
            emptyText={poolTotal === 0 ? t("poolEmpty") : t("noSearchResults")}
          >
            <SortableContext items={pool.map((location) => location.id)} strategy={verticalListSortingStrategy}>
              {pool.map((location) => (
                <LocationRow
                  key={location.id}
                  location={location}
                  disabled={!canEdit}
                  action={
                    canEdit && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => addToTour([location.id])}
                        aria-label={t("addToTour")}
                        title={t("addToTour")}
                      >
                        <ArrowLeft className="size-4" />
                      </Button>
                    )
                  }
                />
              ))}
            </SortableContext>
          </ListColumn>
        </div>

        {/* The row that follows the pointer while dragging. */}
        <DragOverlay>
          {activeLocation && (
            <RowContent
              location={activeLocation}
              position={tourIds.has(activeLocation.id) ? tour.indexOf(activeLocation.id) + 1 : undefined}
              grip={<GripVertical className="size-4 shrink-0 text-muted-foreground" />}
              className="border bg-background shadow-lg"
            />
          )}
        </DragOverlay>
      </DndContext>
    </div>
  );
}

interface ListColumnProps {
  id: Container;
  title: string;
  count: number;
  toolbar: ReactNode;
  isEmpty: boolean;
  emptyText: string;
  children: ReactNode;
}

// One of the two columns: heading + count, a toolbar, and a capped-height
// scroll box that is also a drop area (so an empty list still accepts drops).
function ListColumn({ id, title, count, toolbar, isEmpty, emptyText, children }: ListColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <section className="flex min-w-0 flex-col gap-2 rounded-md border p-3">
      <h2 className="flex items-baseline justify-between gap-2 font-bold underline">
        {title}
        <span className="text-sm font-normal text-muted-foreground no-underline">{count}</span>
      </h2>
      {toolbar}
      <div
        ref={setNodeRef}
        className={cn(
          "flex max-h-[65vh] min-h-32 flex-col gap-1 overflow-y-auto rounded-md bg-muted/30 p-1",
          isOver && "ring-2 ring-primary/40",
        )}
      >
        {children}
        {isEmpty && <p className="p-3 text-sm text-muted-foreground">{emptyText}</p>}
      </div>
    </section>
  );
}

interface LocationRowProps {
  location: KarTrackerDeliveryOrderLocation;
  position?: number;
  disabled: boolean;
  action: ReactNode;
}

// A draggable row. With the mouse/finger the whole row drags; the grip is
// the focusable handle for keyboard dragging (space to pick up, arrows, space
// to drop), so the row itself isn't a button around the arrow button.
function LocationRow({ location, position, disabled, action }: LocationRowProps) {
  const t = useTranslations("karTracker.deliveryOrder");
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({
    id: location.id,
    disabled,
  });
  // dnd-kit types its listeners loosely; the keyboard one goes on the grip, the rest on the row.
  const { onKeyDown, ...pointerListeners } = listeners ?? {};
  const onGripKeyDown = onKeyDown as KeyboardEventHandler<HTMLButtonElement> | undefined;

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      {...pointerListeners}
      className={cn("touch-none", !disabled && "cursor-grab", isDragging && "opacity-40")}
    >
      <RowContent
        location={location}
        position={position}
        action={action}
        grip={
          !disabled && (
            <button
              type="button"
              ref={setActivatorNodeRef}
              {...attributes}
              onKeyDown={onGripKeyDown}
              aria-label={t("dragHandle")}
              title={t("dragHandle")}
              className="shrink-0 cursor-grab rounded text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              <GripVertical className="size-4" />
            </button>
          )
        }
      />
    </div>
  );
}

interface RowContentProps {
  location: KarTrackerDeliveryOrderLocation;
  position?: number;
  action?: ReactNode;
  grip?: ReactNode;
  className?: string;
}

// What a row shows: grip, tour position (right list only), description, name · zone, badge, action button.
function RowContent({ location, position, action, grip, className }: RowContentProps) {
  return (
    <div className={cn("flex items-center gap-2 rounded-md bg-background px-2 py-1.5 text-sm", className)}>
      {grip}
      {position !== undefined && (
        <span className="w-8 shrink-0 text-right font-mono text-muted-foreground tabular-nums">{position}</span>
      )}
      <div className="min-w-0 flex-1">
        {/* Description on top; the name (code) and zone below. Without a description the name moves up. */}
        <div className="truncate font-medium">{location.description || location.name}</div>
        <div className="truncate text-xs text-muted-foreground">
          {location.description ? `${location.name} · ${location.zone_name}` : location.zone_name}
        </div>
      </div>
      <PositionBadge saved={location.terrein_positie} position={position} />
      {/* Pressing the arrow button must not start a drag. */}
      <div onPointerDown={(event) => event.stopPropagation()}>{action}</div>
    </div>
  );
}

// The saved terreinpositie next to the new number, so Save holds no surprises.
// In the tour: "nieuw" (none saved yet), "was 3" in amber (Save changes it) or
// muted (unchanged). Outside the tour: "was 3 → wordt leeg" when Save clears it.
function PositionBadge({ saved, position }: { saved: number | null; position?: number }) {
  const t = useTranslations("karTracker.deliveryOrder");
  const badgeClass = "shrink-0 rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap";

  if (position === undefined) {
    if (saved === null) return null;
    return (
      <span className={cn(badgeClass, "bg-amber-500/15 text-amber-700 dark:text-amber-400")}>
        {t("willBeCleared", { position: saved })}
      </span>
    );
  }
  if (saved === null) {
    return (
      <span className={cn(badgeClass, "bg-blue-500/15 text-blue-700 dark:text-blue-400")}>{t("newInTour")}</span>
    );
  }
  return (
    <span
      className={cn(
        badgeClass,
        saved === position ? "text-muted-foreground" : "bg-amber-500/15 text-amber-700 dark:text-amber-400",
      )}
    >
      {t("previousPosition", { position: saved })}
    </span>
  );
}
