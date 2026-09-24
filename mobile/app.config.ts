// The Expo app configuration. It is a .ts file (not app.json) so ONE codebase
// can produce two distinct apps that install side by side on a phone:
//   test        -> "RWCrew Test", talks to https://test.rwcrew.eu
//   production  -> "RWCrew",      talks to https://rwcrew.eu
// The variant is chosen with the APP_VARIANT environment variable (set per
// build profile in eas.json). Without it we default to "test", so local
// development never touches production by accident.

import type { ExpoConfig } from "expo/config";

// Which of the two apps are we building?
const variant: "test" | "production" = process.env.APP_VARIANT === "production" ? "production" : "test";
const isProduction = variant === "production";

// The API address of the matching website. API_URL (from mobile/.env) can
// override it, e.g. to point at your PC's local backend during development.
const defaultApiUrl = isProduction ? "https://rwcrew.eu" : "https://test.rwcrew.eu";
const apiUrl = process.env.API_URL ?? defaultApiUrl;

const config: ExpoConfig = {
  name: isProduction ? "RWCrew" : "RWCrew Test",
  slug: "rwcrew",
  // The app version. Release builds set this from the mobile-v* git tag.
  version: "0.1.0",
  scheme: isProduction ? "rwcrew" : "rwcrew-test",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "automatic",
  ios: {
    supportsTablet: false,
    // A different bundle id per variant is what lets both apps coexist.
    bundleIdentifier: isProduction ? "eu.rwcrew.app" : "eu.rwcrew.app.test",
    infoPlist: {
      // Texts iOS shows when the app asks for the camera / location.
      NSCameraUsageDescription: "RWCrew uses the camera to attach photos.",
      NSLocationWhenInUseUsageDescription: "RWCrew uses your location to tag where something happened.",
    },
  },
  android: {
    package: isProduction ? "eu.rwcrew.app" : "eu.rwcrew.app.test",
    adaptiveIcon: {
      backgroundColor: "#10261F",
      foregroundImage: "./assets/android-icon-foreground.png",
      backgroundImage: "./assets/android-icon-background.png",
      monochromeImage: "./assets/android-icon-monochrome.png",
    },
    predictiveBackGestureEnabled: false,
  },
  web: { favicon: "./assets/favicon.png" },
  plugins: [
    "expo-router",
    "expo-secure-store",
    // Startup splash: the cream RW mark centred on the icon's dark green.
    // imageWidth is larger than the default because the mark only fills ~60%
    // of splash-icon.png (it keeps padding for Android's safe zone).
    [
      "expo-splash-screen",
      {
        image: "./assets/splash-icon.png",
        backgroundColor: "#10261F",
        imageWidth: 280,
      },
    ],
  ],
  // Expo Router's typed routes are on by default; off here because its
  // generator wrongly lists non-route folders (src/lib, src/components) and
  // then rejects our dynamic paths like /module-3/request/12.
  experiments: { typedRoutes: false },
  // Values the app reads at runtime via expo-constants (see src/lib/config.ts).
  extra: { variant, apiUrl },
};

export default config;
