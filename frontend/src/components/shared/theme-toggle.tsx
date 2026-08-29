"use client";

// A small button in the header that lets the visitor switch between the
// light and dark theme. It shows a sun icon while in dark mode (meaning
// "click to switch to light") and a moon icon while in light mode
// (meaning "click to switch to dark").

import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

// A tiny helper that reports "false" while the page is still being
// rendered on the server (or during the very first browser render before
// hydration), and "true" from then on. next-themes only knows the real
// theme once it has run in the browser (it needs to check localStorage
// first), so we use this to delay showing the real icon until then —
// otherwise the server-rendered page and the first browser render
// wouldn't match, causing a React "hydration mismatch" warning.
function useHasMounted(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
}

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const t = useTranslations("theme");
  const hasMounted = useHasMounted();

  function toggleTheme() {
    setTheme(resolvedTheme === "dark" ? "light" : "dark");
  }

  if (!hasMounted) {
    return (
      <Button variant="ghost" size="icon" disabled aria-hidden="true">
        <Sun className="size-4" />
      </Button>
    );
  }

  const isDark = resolvedTheme === "dark";

  return (
    <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label={t("toggleLabel")} title={t("toggleLabel")}>
      {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </Button>
  );
}
