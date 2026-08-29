// The login page. A server component so we can check — before sending
// any HTML to the browser — whether the visitor is already logged in,
// and skip straight to the landing page if so.

import { getLocale } from "next-intl/server";
import { redirect } from "@/i18n/navigation";
import { getCurrentUserOnServer } from "@/lib/server-auth";
import { LoginForm } from "@/components/landing/login-form";

export default async function LoginPage() {
  const [user, locale] = await Promise.all([getCurrentUserOnServer(), getLocale()]);

  if (user) {
    // Already logged in — no need to show the login form again.
    redirect({ href: "/", locale });
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <LoginForm />
    </div>
  );
}
