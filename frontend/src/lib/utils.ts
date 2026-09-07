import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Strips everything but digits and regroups as Belgian mobile
 * "04XX XX XX XX", capped at 10 digits. Reformats on every keystroke — a
 * known tradeoff for a lightweight form; cursor position isn't specially
 * preserved. Shared by the admin Intervention Requests dialog and the
 * public intervention-request form (both collect a customer phone number).
 */
export function formatPhoneNumber(value: string): string {
  const digits = value.replace(/\D/g, "").slice(0, 10);
  const groups = [digits.slice(0, 4), digits.slice(4, 6), digits.slice(6, 8), digits.slice(8, 10)];
  return groups.filter(Boolean).join(" ");
}
