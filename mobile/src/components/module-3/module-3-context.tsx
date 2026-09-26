// Loads what the current user may do in Intervention Requests once, when
// the module opens, and shares it with every screen inside it. While it
// loads (or if it fails, e.g. no access to the module) the module's screens
// aren't shown at all.

import { createContext, useContext, type ReactNode } from "react";

import { module3Api } from "../../lib/module-api";
import type { Module3Permissions } from "../../lib/types";
import { useAsync } from "../../lib/use-async";
import { ErrorView, Loading } from "../ui";

const PermissionsContext = createContext<Module3Permissions | null>(null);

export function Module3Provider({ children }: { children: ReactNode }) {
  const { data, error, loading, reload } = useAsync(module3Api.permissions);

  if (loading) return <Loading />;
  if (error || data === null) return <ErrorView error={error ?? new Error("No permissions")} onRetry={reload} />;
  return <PermissionsContext.Provider value={data}>{children}</PermissionsContext.Provider>;
}

// What the user may do on the requests screen (view / create / edit).
export function useModule3Permissions(): Module3Permissions {
  const permissions = useContext(PermissionsContext);
  if (permissions === null) throw new Error("useModule3Permissions must be used inside <Module3Provider>");
  return permissions;
}
