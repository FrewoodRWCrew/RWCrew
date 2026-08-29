// The "Mainpage": the tile grid every logged-in user lands on after
// signing in. Rendered on the server so the tiles (and which of them are
// locked) show up immediately, with no loading spinner.

import { getTranslations } from "next-intl/server";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { serverApiFetch } from "@/lib/server-api";
import type { ModuleInfo } from "@/lib/types";
import { ModuleTile } from "@/components/landing/module-tile";

export default async function LandingPage() {
  const t = await getTranslations("landing");

  // The (protected) layout above already guarantees we're logged in, so
  // "user" is never null here in practice — Next.js's request
  // memoization means this doesn't trigger a second network call.
  const [user, modules] = await Promise.all([getCurrentUserOnServer(), serverApiFetch<ModuleInfo[]>("/api/modules")]);

  const accessibleModuleKeys = new Set(user?.accessible_module_keys ?? []);
  const hasAnyAccess = accessibleModuleKeys.size > 0;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
        <p className="text-muted-foreground">{t("subtitle")}</p>
      </div>

      {!hasAnyAccess && (
        <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">{t("noAccess")}</p>
      )}

      {/* A fixed 3x3 grid — there are always exactly 9 modules. */}
      <div className="grid max-w-2xl grid-cols-3 gap-4">
        {modules
          .sort((a, b) => a.sort_order - b.sort_order)
          .map((module) => (
            <ModuleTile key={module.key} module={module} hasAccess={accessibleModuleKeys.has(module.key)} />
          ))}
      </div>
    </div>
  );
}
