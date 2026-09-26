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

// The phone-app download page (module-10) — not a real module, so it gets
// its own small tile instead of a spot in the grid.
const MOBILE_MODULE_KEY = "module-10";

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

  // The "Mobile App" download page isn't a real module, so it's pulled out
  // of the grid and shown as a smaller shortcut tile in the top-right
  // corner, just below the user menu in the header.
  const mobileModule = accessibleModules.find((module) => module.key === MOBILE_MODULE_KEY);
  const gridModules = accessibleModules.filter((module) => module.key !== MOBILE_MODULE_KEY);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        {/* w-27 is about half of one grid column's width below. */}
        {mobileModule && (
          <div className="w-27 shrink-0">
            <ModuleTile module={mobileModule} compact />
          </div>
        )}
      </div>

      {gridModules.length === 0 ? (
        <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">{t("noAccess")}</p>
      ) : (
        <div className="grid max-w-2xl grid-cols-3 gap-4">
          {gridModules.map((module) => (
            <ModuleTile key={module.key} module={module} />
          ))}
        </div>
      )}
    </div>
  );
}
