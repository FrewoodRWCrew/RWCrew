// Runtime settings for this build of the app, read from app.config.ts
// (which decides them per test/production variant).

import Constants from "expo-constants";

// "test" or "production" — which of the two apps this is.
export const APP_VARIANT: "test" | "production" =
  Constants.expoConfig?.extra?.variant === "production" ? "production" : "test";

// The backend address, without a trailing slash.
export const API_URL: string = String(Constants.expoConfig?.extra?.apiUrl ?? "").replace(/\/+$/, "");

// The app version, sent with every request so the backend can refuse builds
// that are too old (HTTP 426, see backend/app/mobile/version_gate.py).
export const APP_VERSION: string = Constants.expoConfig?.version ?? "0.0.0";
