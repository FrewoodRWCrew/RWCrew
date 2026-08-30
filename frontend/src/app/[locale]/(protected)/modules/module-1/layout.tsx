// This layout wraps every Tagscan page (the dashboard and everything
// under access-rights/) with Tagscan's own left-hand menu, the same way
// the site-wide (protected) layout wraps everything with the admin
// sidebar — see components/module-1/tagscan-sidebar.tsx for what shows
// in it and why.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { TagscanMyPermissions } from "@/lib/types";
import { TagscanSidebar } from "@/components/module-1/tagscan-sidebar";

interface TagscanLayoutProps {
  children: React.ReactNode;
}

export default async function TagscanLayout({ children }: TagscanLayoutProps) {
  let permissions: TagscanMyPermissions | null = null;
  let forbidden = false;

  try {
    permissions = await serverApiFetch<TagscanMyPermissions>("/api/modules/module-1/me/permissions");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      forbidden = true;
    } else {
      throw error;
    }
  }

  if (forbidden || !permissions) {
    const tErrors = await getTranslations("errors");
    return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
  }

  return (
    // "-m-6" cancels out the (protected) layout's own page padding so
    // this sub-menu can sit flush against a real border on every side,
    // the same way the site-wide admin sidebar does one level up.
    <div className="-m-6 flex min-h-[calc(100vh-3.5rem)]">
      <TagscanSidebar viewableScreenKeys={permissions.viewable_screen_keys} />
      <div className="min-w-0 flex-1 p-6">{children}</div>
    </div>
  );
}
