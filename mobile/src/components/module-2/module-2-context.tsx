// Loads what the current user may do in KarScan once, when the module opens,
// and shares it with every screen inside it. While it loads (or if it fails,
// e.g. no access to KarTracker) the module's screens aren't shown at all.

import { createContext, useContext, type ReactNode } from "react";

import { module2Api } from "../../lib/module-api";
import type { Module2Permissions } from "../../lib/types";
import { useAsync } from "../../lib/use-async";
import { ErrorView, Loading } from "../ui";

const PermissionsContext = createContext<Module2Permissions | null>(null);

export function Module2Provider({ children }: { children: ReactNode }) {
  const { data, error, loading, reload } = useAsync(module2Api.permissions);

  if (loading) return <Loading />;
  if (error || data === null) return <ErrorView error={error ?? new Error("No permissions")} onRetry={reload} />;
  return <PermissionsContext.Provider value={data}>{children}</PermissionsContext.Provider>;
}

// What the user may do on "Manuele kar beweging" (look up / register).
export function useModule2Permissions(): Module2Permissions {
  const permissions = useContext(PermissionsContext);
  if (permissions === null) throw new Error("useModule2Permissions must be used inside <Module2Provider>");
  return permissions;
}
