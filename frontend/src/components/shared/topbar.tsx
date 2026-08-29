// The header shown at the top of every protected page: the app name on
// the left, and the theme toggle / language switcher / user menu on the
// right.

import Image from "next/image";
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import type { CurrentUser } from "@/lib/types";
import { LanguageSwitcher } from "@/components/shared/language-switcher";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { UserMenu } from "@/components/shared/user-menu";

interface TopbarProps {
  user: CurrentUser;
}

export function Topbar({ user }: TopbarProps) {
  const t = useTranslations("common");

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b bg-background px-4">
      <Link href="/" className="flex items-center gap-2">
        {/* The logo is drawn in black. "dark:invert" flips it to white
            (without affecting its transparent background) so it stays
            visible against RW Crew's dark theme, which is the default. */}
        <Image src="/altsien-logo.png" alt="Altsien" width={28} height={33} className="h-7 w-auto dark:invert" priority />
        <span className="text-sm font-semibold tracking-tight">{t("appName")}</span>
      </Link>
      <div className="flex items-center gap-1">
        <LanguageSwitcher />
        <ThemeToggle />
        <UserMenu user={user} />
      </div>
    </header>
  );
}
