// The "Mainpage": the tile grid every logged-in user lands on after
// signing in. Rendered on the server so the tiles show up immediately,
// with no loading spinner. Only modules the user actually has access to
// are shown — see ModuleTile for why a locked-tile treatment is no
// longer needed.

import { getTranslations } from "next-intl/server";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { serverApiFetch } from "@/lib/server-api";
import type { ModuleInfo } from "@/lib/types";
import { ModuleTile } from "@/components/landing/module-tile";
import { getModuleTranslationKey } from "@/lib/module-theme";

export default async function LandingPage() {
  const t = await getTranslations("landing");
  // Root translator (no namespace) so we can look up each module's own
  // "moduleTitle" key, wherever it lives in messages/*.json — see
  // getModuleTranslationKey for why the backend's module name alone isn't
  // enough to localize the tile.
  const tRoot = await getTranslations();

  // The (protected) layout above already guarantees we're logged in, so
  // "user" is never null here in practice — Next.js's request
  // memoization means this doesn't trigger a second network call.
  const [user, modules] = await Promise.all([getCurrentUserOnServer(), serverApiFetch<ModuleInfo[]>("/api/modules")]);

  const accessibleModuleKeys = new Set(user?.accessible_module_keys ?? []);
  const accessibleModules = modules
    .filter((module) => accessibleModuleKeys.has(module.key))
    .sort((a, b) => a.sort_order - b.sort_order)
    .map((module) => {
      const translationKey = getModuleTranslationKey(module.key);
      return translationKey ? { ...module, name: tRoot(translationKey) } : module;
    });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
        <p className="text-muted-foreground">{t("subtitle")}</p>
      </div>

      {accessibleModules.length === 0 ? (
        <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">{t("noAccess")}</p>
      ) : (
        <div className="grid max-w-2xl grid-cols-3 gap-4">
          {accessibleModules.map((module) => (
            <ModuleTile key={module.key} module={module} />
          ))}
        </div>
      )}
    </div>
  );
}
