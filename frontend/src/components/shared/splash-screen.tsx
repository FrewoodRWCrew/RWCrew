"use client";

// A full-screen splash shown for a few seconds right when the app first
// loads, before the login (or any other) page becomes visible — the same
// idea as the launch screen of a native mobile app. It shows both the
// Altsien and Live Nation logos, since RW Crew is built for Altsien in
// partnership with Live Nation.
//
// This component lives in the TRUE root layout (src/app/layout.tsx),
// which only re-mounts on a full page load — not when navigating between
// pages inside the app (e.g. from the login page to the Mainpage after
// signing in) — so the splash only ever appears once per "app start",
// exactly as asked for.

import Image from "next/image";
import { useEffect, useState } from "react";

// How long the splash stays fully visible before it starts fading away.
const SPLASH_VISIBLE_MS = 2500;
// How long the fade-out transition itself takes, once it starts.
const SPLASH_FADE_MS = 500;

interface SplashScreenProps {
  // Passed in already translated from the server (see src/app/layout.tsx),
  // since this component lives OUTSIDE next-intl's client-side message
  // provider — that provider only wraps the "[locale]" part of the app,
  // on purpose, so switching languages doesn't remount this component.
  loadingText: string;
}

export function SplashScreen({ loadingText }: SplashScreenProps) {
  // "shown" controls whether this component renders anything at all —
  // once the fade-out finishes, we stop rendering it completely so it
  // can't block clicks on the real page underneath.
  const [shown, setShown] = useState(true);
  // "fadingOut" only controls the CSS opacity transition; kept separate
  // from "shown" so the fade actually has time to animate before the
  // component disappears.
  const [fadingOut, setFadingOut] = useState(false);

  useEffect(() => {
    const startFadeTimer = setTimeout(() => setFadingOut(true), SPLASH_VISIBLE_MS);
    const removeTimer = setTimeout(() => setShown(false), SPLASH_VISIBLE_MS + SPLASH_FADE_MS);

    // Clean up both timers if this component were ever removed early.
    return () => {
      clearTimeout(startFadeTimer);
      clearTimeout(removeTimer);
    };
  }, []);

  if (!shown) {
    return null;
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed inset-0 z-50 flex flex-col items-center justify-center gap-10 bg-background transition-opacity ease-in-out ${
        fadingOut ? "pointer-events-none opacity-0" : "opacity-100"
      }`}
      style={{ transitionDuration: `${SPLASH_FADE_MS}ms` }}
    >
      {/* Screen-reader-only announcement — the logos and progress bar
          below are purely visual. */}
      <span className="sr-only">{loadingText}</span>

      {/* Both logos share one tile, on a white background (the Altsien
          mark is drawn in black, so it needs a light backdrop to stay
          visible no matter which theme is active) with both logos set
          to the exact same height, side by side. */}
      <div className="flex items-center gap-8 rounded-2xl bg-white p-6 shadow-lg sm:gap-10 sm:p-8">
        <Image
          src="/altsien-logo.png"
          alt="Altsien"
          width={80}
          height={94}
          className="h-16 w-auto object-contain sm:h-20"
          priority
        />
        <Image
          src="/livenation-logo.jpg"
          alt="Live Nation"
          width={200}
          height={200}
          className="h-16 w-auto object-contain sm:h-20"
          priority
        />
      </div>

      <div className="flex w-48 flex-col items-center gap-3 sm:w-56">
        {/* An empty track with a filled bar that grows to 100% width over
            exactly the time the splash is shown, via the "splash-progress"
            keyframes defined in globals.css. */}
        <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-primary"
            style={{ animation: `splash-progress ${SPLASH_VISIBLE_MS}ms linear forwards` }}
          />
        </div>
        <p className="text-xs text-muted-foreground">{loadingText}</p>
      </div>
    </div>
  );
}
