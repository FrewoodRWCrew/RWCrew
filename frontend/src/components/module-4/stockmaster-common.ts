// Small shared pieces of the StockMaster screens: the module's base URL,
// the bookings in the order of the warehouse process (the same order as
// the "Akties" menu), which screen's right allows which booking, how the
// backend's "code|param|..." errors become a friendly translated message,
// and the window event a screen sends after it changed stock (so the
// minimum-stock banner re-counts).

import { ApiError } from "@/lib/api";
import type { StockMasterAction, StockMasterMyPermissions } from "@/lib/types";

export const STOCKMASTER_BASE = "/modules/module-4";

/** Window event a StockMaster screen dispatches after a booking. */
export const STOCK_CHANGED_EVENT = "stockmaster:stock-changed";

/** Tell other parts of the screen (the banner) that stock changed. */
export function announceStockChanged() {
  window.dispatchEvent(new Event(STOCK_CHANGED_EVENT));
}

/** The bookings in the order of the warehouse process. */
export const ACTION_ORDER: StockMasterAction[] = [
  "book_in",
  "kar_load",
  "book_out",
  "kar_dispatch",
  "kar_return",
  "kar_unload",
  "count",
];

/** The page of each booking (under STOCKMASTER_BASE). */
export const ACTION_PATHS: Record<StockMasterAction, string> = {
  book_in: "/book-in",
  kar_load: "/kars/load",
  book_out: "/book-out",
  kar_dispatch: "/kars/dispatch",
  kar_return: "/kars/return",
  kar_unload: "/kars/unload",
  count: "/count",
};

/** The screen whose "create" right allows each booking. */
export const ACTION_SCREENS: Record<StockMasterAction, string> = {
  book_in: "stockmaster.stock",
  kar_load: "stockmaster.kars",
  book_out: "stockmaster.stock",
  kar_dispatch: "stockmaster.kars",
  kar_return: "stockmaster.kars",
  kar_unload: "stockmaster.kars",
  count: "stockmaster.count",
};

/** The actions that work on one kar. */
export const KAR_ACTIONS: StockMasterAction[] = ["kar_load", "kar_dispatch", "kar_return", "kar_unload"];

/** Whether the user may make this booking ("Inboeken" is also allowed
 *  from "Te bestellen"). */
export function canBook(permissions: StockMasterMyPermissions, action: StockMasterAction): boolean {
  if (permissions.creatable_screen_keys.includes(ACTION_SCREENS[action])) return true;
  return action === "book_in" && permissions.creatable_screen_keys.includes("stockmaster.orderneeds");
}

/** Shorthand checks on the user's StockMaster rights. */
export function hasRight(
  permissions: StockMasterMyPermissions,
  screen: string,
  action: "view" | "create" | "edit" | "delete",
): boolean {
  const keys = {
    view: permissions.viewable_screen_keys,
    create: permissions.creatable_screen_keys,
    edit: permissions.editable_screen_keys,
    delete: permissions.deletable_screen_keys,
  }[action];
  return keys.includes(`stockmaster.${screen}`);
}

type Translate = {
  (key: string, values?: Record<string, string | number>): string;
  has: (key: string) => boolean;
};

/** Turn a failed request into a friendly message. The backend answers a
 *  broken stock rule with "code|param|param" (e.g.
 *  "insufficient_stock|Walkie-lader|3|K043"), translated under
 *  stockMaster.errors.<code> with {p1}, {p2}, {p3}. "free" as a place reads
 *  as "vrije voorraad". */
export function stockErrorMessage(t: Translate, error: unknown): string {
  if (!(error instanceof ApiError)) return t("errors.generic");
  const [code, ...params] = error.message.split("|");
  const values: Record<string, string> = {};
  params.forEach((param, index) => {
    values[`p${index + 1}`] = param === "free" ? t("common.freeStock") : param;
  });
  if (t.has(`errors.${code}`)) return t(`errors.${code}`, values);
  if (error.status === 403) return t("errors.not_allowed");
  return t("errors.generic");
}

/** Read a remembered filter value (per browser), never failing. */
export function readRemembered<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(`stockmaster.${key}`);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

/** Remember a filter value (per browser), never failing. */
export function remember(key: string, value: unknown) {
  try {
    window.localStorage.setItem(`stockmaster.${key}`, JSON.stringify(value));
  } catch {
    // Storage blocked (private window): the filter just isn't remembered.
  }
}
