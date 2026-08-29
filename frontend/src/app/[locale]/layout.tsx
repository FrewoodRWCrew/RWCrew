// This layout is scoped to one language segment ("/nl/..." or
// "/en/..."). It only handles language concerns — validating the segment
// and making the right translated text available — so switching
// languages re-renders just this part of the tree, not the whole
// document (see the true root layout in src/app/layout.tsx for why that
// separation matters).

import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { routing, type AppLocale } from "@/i18n/routing";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

interface LocaleLayoutProps {
  children: React.ReactNode;
  // In this Next.js version, route params are provided as a Promise.
  params: Promise<{ locale: string }>;
}

export default async function LocaleLayout({ children, params }: LocaleLayoutProps) {
  const { locale } = await params;

  // Reject any language that isn't one of ours (e.g. someone visiting
  // "/fr/...") with a normal 404, instead of silently showing something
  // in the wrong language.
  if (!routing.locales.includes(locale as AppLocale)) {
    notFound();
  }

  // Tell next-intl which language this specific request is for, so
  // every server component rendered below can look up the right text.
  setRequestLocale(locale);

  const messages = await getMessages();

  return <NextIntlClientProvider messages={messages}>{children}</NextIntlClientProvider>;
}
