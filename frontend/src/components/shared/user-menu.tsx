"use client";

// The header control showing the logged-in user's name, with a dropdown
// to log out.

import { LogOut } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { logout } from "@/lib/api";
import type { CurrentUser } from "@/lib/types";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface UserMenuProps {
  user: CurrentUser;
}

/** Turn "RW Crew Admin" into "RC" for the little round avatar. */
function getInitials(displayName: string): string {
  const words = displayName.trim().split(/\s+/);
  const firstLetters = words.slice(0, 2).map((word) => word.charAt(0).toUpperCase());
  return firstLetters.join("") || "?";
}

export function UserMenu({ user }: UserMenuProps) {
  const t = useTranslations("common");
  const router = useRouter();

  async function handleLogout() {
    // Ask the backend to end this session (revoking the refresh token
    // and clearing the auth cookies)...
    await logout();
    // ...then send the browser to the login page.
    router.push("/login");
    // A full refresh makes sure every server component re-checks the
    // (now logged-out) session, instead of showing stale cached data.
    router.refresh();
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" className="flex items-center gap-2 px-2">
            <Avatar className="size-7">
              <AvatarFallback>{getInitials(user.display_name)}</AvatarFallback>
            </Avatar>
            <span className="hidden text-sm font-medium sm:inline">{user.display_name}</span>
          </Button>
        }
      />
      <DropdownMenuContent align="end">
        <DropdownMenuLabel className="max-w-56 truncate">{user.email}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout}>
          <LogOut className="size-4" />
          {t("logout")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
