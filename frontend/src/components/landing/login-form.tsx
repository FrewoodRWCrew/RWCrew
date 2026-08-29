"use client";

// The actual interactive login form: an email field, a password field,
// and a submit button. Kept as its own small component so the page file
// itself can stay a server component (see the login page.tsx), which is
// what lets us redirect an already-logged-in visitor before any of this
// client-side code even loads.

import { useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import { ApiError, login } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginForm() {
  const t = useTranslations("login");
  const tCommon = useTranslations("common");
  const router = useRouter();

  // The two form fields the visitor fills in.
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  // Whether we're currently waiting for the backend to respond.
  const [isSubmitting, setIsSubmitting] = useState(false);
  // Set to an error message if the last login attempt failed.
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    // Stop the browser from doing its own full-page form submission —
    // we want to send the request ourselves and handle the result.
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await login(email, password);
      // A successful login already set our auth cookies. Send the
      // visitor to the landing page, and refresh so the server-rendered
      // layout picks up the new, now-logged-in session.
      router.push("/");
      router.refresh();
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setErrorMessage(t("invalidCredentials"));
      } else {
        setErrorMessage(t("genericError"));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle>{t("title")}</CardTitle>
        <CardDescription>{tCommon("appName")}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="email">{t("emailLabel")}</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="password">{t("passwordLabel")}</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {errorMessage && <p className="text-sm text-destructive">{errorMessage}</p>}

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? tCommon("loading") : t("submit")}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
