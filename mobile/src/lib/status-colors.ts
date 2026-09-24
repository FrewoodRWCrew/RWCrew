// The colour of an Intervention Status (chosen by an admin on the web's
// "Intervention Statuses" screen). The hex values are Tailwind's own shades,
// copied from the web app's STATUS_COLOR_CHART_HEX, so a status looks the
// same on the phone as on the web.

const STATUS_COLORS: Record<string, { light: string; dark: string }> = {
  red: { light: "#dc2626", dark: "#f87171" },
  orange: { light: "#ea580c", dark: "#fb923c" },
  amber: { light: "#d97706", dark: "#fbbf24" },
  green: { light: "#16a34a", dark: "#4ade80" },
  teal: { light: "#0d9488", dark: "#2dd4bf" },
  blue: { light: "#2563eb", dark: "#60a5fa" },
  indigo: { light: "#4f46e5", dark: "#818cf8" },
  purple: { light: "#9333ea", dark: "#c084fc" },
  gray: { light: "#4b5563", dark: "#9ca3af" },
};

// The colour for a status key ("red", "green", ...); unknown keys fall back to gray.
export function statusColor(color: string, isDark: boolean): string {
  const entry = STATUS_COLORS[color] ?? STATUS_COLORS.gray;
  return isDark ? entry.dark : entry.light;
}
