// Shared by KarTracker's Karcode Simulator and Instellingen screens: turning a
// failed karcode request into a readable message. The backend answers a bad
// formula or kar number with "code|param" (e.g. "unknown_function|SUM", see
// backend module_2/karcode_formula.py), translated under
// karTracker.karcode.errors.<code> with {p1}.

import { ApiError } from "@/lib/api";

/** The bits of next-intl's translator (namespace "karTracker.karcode") used here. */
type Translate = {
  (key: string, values?: Record<string, string | number>): string;
  has: (key: string) => boolean;
};

export function karcodeErrorMessage(t: Translate, error: unknown): string {
  if (!(error instanceof ApiError)) return t("errors.generic");
  const [code, ...params] = error.message.split("|");
  const values: Record<string, string> = {};
  params.forEach((param, index) => {
    values[`p${index + 1}`] = param;
  });
  if (t.has(`errors.${code}`)) return t(`errors.${code}`, values);
  if (error.status === 403) return t("errors.not_allowed");
  return t("errors.generic");
}
