// Every one of the 9 modules currently shows the exact same placeholder
// content (its name, the visitor's role, and a "coming soon" message).
// This shared component holds that logic once; each module's own
// page.tsx (see app/[locale]/(protected)/modules/module-1/page.tsx etc.)
// just calls it with its own module key — the same "shared behaviour,
// thin per-module file" pattern used on the backend (see
// backend/app/modules/common.py).

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import { getModuleTheme } from "@/lib/module-theme";
import type { ModuleStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ModulePlaceholderPageProps {
  moduleKey: string;
}

export async function ModulePlaceholderPage({ moduleKey }: ModulePlaceholderPageProps) {
  const t = await getTranslations("modulePage");
  const tErrors = await getTranslations("errors");
  const tRoles = await getTranslations("roles");
  const theme = getModuleTheme(moduleKey);

  let status: ModuleStatus | null = null;
  let forbidden = false;

  try {
    status = await serverApiFetch<ModuleStatus>(`/api/modules/${moduleKey}/status`);
  } catch (error) {
    // A visitor without access to this module (e.g. one who typed the
    // URL directly instead of clicking a tile) gets a clear message
    // instead of a crashed page.
    if (error instanceof ServerApiError && error.status === 403) {
      forbidden = true;
    } else {
      throw error;
    }
  }

  if (forbidden || !status) {
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className={cn("inline-flex w-fit items-center rounded-full px-3 py-1 text-xs font-medium", theme.badgeClassName)}>
        {status.module_name}
      </div>
      <h1 className="text-2xl font-semibold tracking-tight">{status.module_name}</h1>
      <p className="text-muted-foreground">{t("comingSoon")}</p>
      <p className="text-sm">{status.your_role ? t("yourRole", { role: tRoles(status.your_role) }) : t("noRole")}</p>
    </div>
  );
}
