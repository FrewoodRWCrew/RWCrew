// This layout wraps every page that requires being logged in: the
// landing tile grid, the admin screens, and all 9 modules. It checks who
// is logged in ON THE SERVER (so a logged-out visitor is redirected
// before any protected content is ever sent to their browser), and then
// renders the shared app shell (the admin sidebar, if applicable, and
// the top header bar) around the actual page content.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { AdminSidebar } from "@/components/shared/admin-sidebar";
import { Topbar } from "@/components/shared/topbar";

interface ProtectedLayoutProps {
  children: React.ReactNode;
}

export default async function ProtectedLayout({ children }: ProtectedLayoutProps) {
  const [user, locale] = await Promise.all([getCurrentUserOnServer(), getLocale()]);

  if (!user) {
    // Not logged in (or the session expired) — send them to the login
    // page instead of showing any protected content. redirect() never
    // actually returns (it throws a special error Next.js catches), but
    // we still return right after it so TypeScript can tell that "user"
    // is never null below this point.
    redirect({ href: "/login", locale });
    return null;
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Only the super admin sees the left-hand admin menu — everyone
          else just sees the tile grid / module pages full-width. */}
      {user.is_super_admin && <AdminSidebar />}
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar user={user} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
