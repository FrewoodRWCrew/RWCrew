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
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
