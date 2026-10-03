"use client";

// This component makes light/dark theme switching available to the whole
// app. It's a thin wrapper around the "next-themes" library, which does
// the actual work of adding/removing the "dark" class on the <html>
// element and remembering the visitor's choice in their browser.

import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ComponentProps } from "react";

export function ThemeProvider({ children, ...props }: ComponentProps<typeof NextThemesProvider>) {
  return (
    <NextThemesProvider
      // Our CSS (see globals.css) toggles colours based on a "dark" class
      // on a parent element, so we tell next-themes to use that approach.
      attribute="class"
      // RW Crew starts in dark mode for every new visitor...
      defaultTheme="dark"
      // ...and does NOT automatically follow the visitor's operating
      // system preference — dark stays the default until they explicitly
      // switch to light mode themselves.
      enableSystem={false}
      // next-themes renders a small inline <script> that sets the theme class
      // before the page paints. It only has to run from the server's HTML;
      // when React renders it again in the browser, React 19 warns
      // "Encountered a script tag while rendering React component". Giving
      // the browser-side copy a non-JavaScript type silences that without
      // changing what the server sends (next-themes already suppresses the
      // hydration mismatch on this tag).
      scriptProps={typeof window === "undefined" ? undefined : { type: "application/json" }}
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
