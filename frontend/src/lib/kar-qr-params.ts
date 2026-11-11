// The query parameters the karblad's QR code carries to the public kar page
// (`/kar?team_id=&cart_number=&delivery_location=&zone=`, built by the
// backend's module_2/karblad_pdf.py build_kar_qr_url). The landing page and
// both its forms read them with these helpers, and the tiles pass them on
// unchanged, so the forms stay prefilled.

export type RawSearchParams = { [key: string]: string | string[] | undefined };

/** What the QR code tells us about the kar (every field optional). */
export interface KarQrParams {
  team_id?: string;
  team_name?: string;
  cart_number?: string;
  delivery_location?: string;
  zone?: string;
}

const KEYS = ["team_id", "team_name", "cart_number", "delivery_location", "zone"] as const;

/** The first value of a query param, if it was given as a plain string —
 *  a QR-encoded URL never repeats a key, so a string[] here would mean a
 *  malformed link; treat that the same as "not provided". */
export function firstParam(value: string | string[] | undefined): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

/** The kar's fields out of a page's searchParams. */
export function readKarQrParams(params: RawSearchParams): KarQrParams {
  const result: KarQrParams = {};
  for (const key of KEYS) {
    const value = firstParam(params[key]);
    if (value) result[key] = value;
  }
  return result;
}

/** The same fields as a query string ("" when none, else starting with "?"). */
export function karQrQuery(params: KarQrParams | RawSearchParams): string {
  const search = new URLSearchParams();
  for (const key of KEYS) {
    const value = firstParam(params[key]);
    if (value) search.set(key, value);
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}
