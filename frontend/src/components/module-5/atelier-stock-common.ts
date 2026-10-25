// Small shared pieces of Atelier's stock screens (block 3): their routes, the
// event a booking sends so the minimum-stock banner re-counts, and the
// translation of the backend's "code|param|…" stock errors.

import { ApiError } from "@/lib/api";

export const ATELIER_STOCK_BASE = "/modules/module-5/stock";

/** Dispatched on window after a booking, so the minimum-stock banner re-counts. */
export const ATELIER_STOCK_CHANGED_EVENT = "atelier-stock-changed";

type Translate = {
  (key: string, values?: Record<string, string | number>): string;
  has: (key: string) => boolean;
};

/** Turn a failed booking into a friendly message. The backend answers a
 *  broken stock rule with "code|param|param" (e.g.
 *  "insufficient_stock|T-shirt · M (men)|3|to_wash"), translated under
 *  atelier.stock.errors.<code> with {p1}, {p2}, {p3}; a status code as
 *  parameter is shown as its translated name. `t` is the atelier.stock
 *  translator. */
export function atelierStockErrorMessage(t: Translate, error: unknown): string {
  if (!(error instanceof ApiError)) return t("errors.generic");
  const [code, ...params] = error.message.split("|");
  const values: Record<string, string> = {};
  params.forEach((param, index) => {
    values[`p${index + 1}`] = t.has(`statuses.${param}`) ? t(`statuses.${param}`) : param;
  });
  if (t.has(`errors.${code}`)) return t(`errors.${code}`, values);
  if (error.status === 403) return t("errors.not_allowed");
  return t("errors.generic");
}
