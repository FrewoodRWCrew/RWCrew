// Module 10 ("Mobile App"): the download page for the smartphone app. It
// shows the install steps and links per platform, the latest version and a
// short changelog, all read from the backend (GET /api/modules/module-10/
// app-info, which comes from the environment's settings), so publishing a new
// phone build never needs a change here.

import { getTranslations } from "next-intl/server";

import { Button } from "@/components/ui/button";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import { getModuleTheme } from "@/lib/module-theme";
import type { MobileAppInfo } from "@/lib/types";
import { cn } from "@/lib/utils";

export default async function MobileAppPage() {
  const t = await getTranslations("mobileApp");
  const tErrors = await getTranslations("errors");
  const theme = getModuleTheme("module-10");

  // Load the links/version. A visitor without module access gets a clear
  // message instead of a crashed page (same approach as ModulePlaceholderPage).
  let info: MobileAppInfo;
  try {
    // /status enforces module access; /app-info only needs a login.
    await serverApiFetch("/api/modules/module-10/status");
    info = await serverApiFetch<MobileAppInfo>("/api/modules/module-10/app-info");
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
      <h1 className="text-2xl font-semibold tracking-tight underline">{t("title")}</h1>
      <p className="text-muted-foreground">{t("intro")}</p>
      {info.latest_version && <p className="text-sm">{t("latestVersion", { version: info.latest_version })}</p>}

      {/* One card per platform; a platform without a configured link shows "not available yet". */}
      <section className="flex flex-col gap-2 rounded-md border p-4">
        <h2 className="font-semibold">{t("iosTitle")}</h2>
        <ol className="list-decimal pl-5 text-sm text-muted-foreground">
          <li>{t("iosStep1")}</li>
          <li>{t("iosStep2")}</li>
        </ol>
        {info.ios_testflight_url ? (
          <Button render={<a href={info.ios_testflight_url} target="_blank" rel="noreferrer" />} className="w-fit">
            {t("iosButton")}
          </Button>
        ) : (
          <p className="text-sm text-muted-foreground">{t("notAvailable")}</p>
        )}
      </section>

      <section className="flex flex-col gap-2 rounded-md border p-4">
        <h2 className="font-semibold">{t("androidTitle")}</h2>
        <ol className="list-decimal pl-5 text-sm text-muted-foreground">
          <li>{t("androidStep1")}</li>
          <li>{t("androidStep2")}</li>
        </ol>
        {info.android_download_url ? (
          <Button render={<a href={info.android_download_url} target="_blank" rel="noreferrer" />} className="w-fit">
            {t("androidButton")}
          </Button>
        ) : (
          <p className="text-sm text-muted-foreground">{t("notAvailable")}</p>
        )}
      </section>

      {info.changelog.length > 0 && (
        <section className="flex flex-col gap-2">
          <h2 className="font-semibold">{t("changelogTitle")}</h2>
          <ul className="list-disc pl-5 text-sm">
            {info.changelog.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
