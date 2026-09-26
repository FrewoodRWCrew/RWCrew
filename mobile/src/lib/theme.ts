// The app's colours for light and dark mode. Screens call useColors() and
// get the set matching the phone's current appearance.

import { useColorScheme } from "react-native";

const light = {
  background: "#ffffff",
  card: "#f4f4f5",
  text: "#111827",
  muted: "#6b7280",
  border: "#d1d5db",
  inputBackground: "#ffffff",
  danger: "#dc2626",
  brand: "#16a34a",
  onBrand: "#ffffff",
};

const dark: typeof light = {
  background: "#0a0a0a",
  card: "#1c1c1e",
  text: "#f4f4f5",
  muted: "#9ca3af",
  border: "#3f3f46",
  inputBackground: "#1c1c1e",
  danger: "#f87171",
  brand: "#22c55e",
  onBrand: "#0a0a0a",
};

export type Colors = typeof light;

export function useColors(): Colors {
  return useColorScheme() === "dark" ? dark : light;
}
