// Small shared helpers for Atelier's sizes: the fixed fit order (the same as
// FITS in the backend) and how a size is written everywhere ("M · Heren").

import type { AtelierFit, AtelierSize } from "@/lib/types";

/** The fits in the order the screens group them. */
export const ATELIER_FITS: AtelierFit[] = ["women", "men", "unisex"];

/** Sizes grouped by fit, then in their own order (as the backend sorts them). */
export function sortSizes(sizes: AtelierSize[]): AtelierSize[] {
  return [...sizes].sort(
    (a, b) =>
      ATELIER_FITS.indexOf(a.fit) - ATELIER_FITS.indexOf(b.fit) ||
      a.sort_order - b.sort_order ||
      a.name.localeCompare(b.name),
  );
}

/** "M · Heren", given the translated fit name. */
export function sizeLabel(size: AtelierSize, fitLabel: (fit: AtelierFit) => string): string {
  return `${size.name} · ${fitLabel(size.fit)}`;
}
