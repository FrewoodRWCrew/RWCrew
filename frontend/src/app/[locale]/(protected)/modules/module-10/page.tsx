// Module 10 ("Mobile App"): the install page for the phone app. The phone app
// is the PWA under /m (same Next.js site, see CLAUDE.md "Phone section"), so
// there is nothing to download: the page shows a QR code and link to /m, plus
// the "Add to Home Screen" steps per platform. The link and QR code come from
// the backend (GET /api/modules/module-10/install-info, built from the
// environment's APP_PUBLIC_URL), so test and production each point at their own site.

import { getTranslations } from "next-intl/server";

import { CopyInstallLink } from "@/components/module-10/copy-install-link";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import { getModuleTheme } from "@/lib/module-theme";
import type { PwaInstallInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

export default async function MobileAppPage() {
  const t = await getTranslations("mobileApp");
  const tErrors = await getTranslations("errors");
  const theme = getModuleTheme("module-10");

  // Load the link and QR code. A visitor without module access gets a clear
  // message instead of a crashed page (same approach as ModulePlaceholderPage).
  let info: PwaInstallInfo;
  try {
    // /status enforces module access; /install-info only needs a login.
    await serverApiFetch("/api/modules/module-10/status");
    info = await serverApiFetch<PwaInstallInfo>("/api/modules/module-10/install-info");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <div className={cn("inline-flex w-fit items-center rounded-full px-3 py-1 text-xs font-medium", theme.badgeClassName)}>
        {t("title")}
      </div>
      <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
      <p className="text-muted-foreground">{t("intro")}</p>

      {/* Step 1: open the phone app's address on the phone, by QR code or link. */}
      <section className="flex flex-col gap-3 rounded-md border p-4">
        <h2 className="font-semibold">{t("openTitle")}</h2>
        {info.install_url && info.qr_code_data_uri ? (
          <>
            <p className="text-sm text-muted-foreground">{t("openDescription")}</p>
            {/* A data: URI from our own backend, so a plain <img> without next/image is fine. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={info.qr_code_data_uri}
              alt={t("qrAlt")}
              className="size-48 rounded-md border bg-white p-2"
            />
            <CopyInstallLink installUrl={info.install_url} />
          </>
        ) : (
          <p className="text-sm text-muted-foreground">{t("notConfigured")}</p>
        )}
      </section>

      {/* Step 2: add it to the home screen; the steps differ per platform. */}
      <section className="flex flex-col gap-2 rounded-md border p-4">
        <h2 className="font-semibold">{t("iosTitle")}</h2>
        <ol className="list-decimal pl-5 text-sm text-muted-foreground">
          <li>{t("iosStep1")}</li>
          <li>{t("iosStep2")}</li>
          <li>{t("iosStep3")}</li>
        </ol>
      </section>

      <section className="flex flex-col gap-2 rounded-md border p-4">
        <h2 className="font-semibold">{t("androidTitle")}</h2>
        <ol className="list-decimal pl-5 text-sm text-muted-foreground">
          <li>{t("androidStep1")}</li>
          <li>{t("androidStep2")}</li>
          <li>{t("androidStep3")}</li>
        </ol>
      </section>

      <p className="text-sm text-muted-foreground">{t("permissionsNote")}</p>
    </div>
  );
}
