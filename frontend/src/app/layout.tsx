// This is the true root layout: the one and only place the <html> and
// <body> tags are rendered. It stays the same no matter which language
// segment ("/nl/..." or "/en/...") is being shown, which matters because
// it also sets up light/dark theming (ThemeProvider) — if this lived
// inside the language-specific layout instead, switching languages would
// unnecessarily remount the whole document (theme included) every time.

import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { Toaster } from "@/components/ui/sonner";
import { SplashScreen } from "@/components/shared/splash-screen";
import { ThemeProvider } from "@/components/shared/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  title: "RW Crew",
  description: "RW Crew management application",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Even though the current language is decided by the "[locale]" URL
  // segment (handled one level down), next-intl still lets us read it
  // here too, purely so the <html lang="..."> attribute is correct.
  const locale = await getLocale();
  // Translated on the server so the splash screen's text is in the
  // right language without needing next-intl's client-side message
  // provider (see splash-screen.tsx for why that matters here).
  const t = await getTranslations("common");

  return (
    <html lang={locale} suppressHydrationWarning>
      <body className="antialiased">
        {/* suppressHydrationWarning above and on <html> is needed because
            next-themes updates the "dark" class on the client, before
            React would otherwise expect it — this is next-themes' own
            documented, safe way of avoiding a mismatch warning. */}
        <ThemeProvider>
          <SplashScreen loadingText={t("loading")} />
          {children}
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
