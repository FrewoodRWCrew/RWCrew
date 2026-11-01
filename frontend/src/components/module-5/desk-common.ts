// Shared by Atelier's counter-desk screens (block 4): the translation of the
// backend's "code|param|…" errors, and saving a downloaded Excel file. Desk
// rules are translated under atelier.desk.errors.<code>; stock rules (e.g.
// insufficient_stock) fall back to atelier.stock.errors.<code>.

import { ApiError } from "@/lib/api";
import { atelierStockErrorMessage } from "@/components/module-5/atelier-stock-common";

type Translate = {
  (key: string, values?: Record<string, string | number>): string;
  has: (key: string) => boolean;
};

/** Saves a list's Excel file as `<name>-<festival>.xlsx` in the browser's downloads. */
export function saveExcel(blob: Blob, name: string, festivalName: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${name}-${festivalName.replace(/[^\p{L}\p{N}]+/gu, "-")}.xlsx`;
  link.click();
  URL.revokeObjectURL(url);
}

/** A failed desk action as a friendly message (`tDesk` = atelier.desk, `tStock` = atelier.stock). */
export function atelierDeskErrorMessage(tDesk: Translate, tStock: Translate, error: unknown): string {
  if (error instanceof ApiError) {
    const [code, ...params] = error.message.split("|");
    if (tDesk.has(`errors.${code}`)) {
      const values: Record<string, string> = {};
      params.forEach((param, index) => {
        values[`p${index + 1}`] = param;
      });
      return tDesk(`errors.${code}`, values);
    }
  }
  return atelierStockErrorMessage(tStock, error);
}
