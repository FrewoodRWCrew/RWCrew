// The root of the app: sets up the session (who is logged in) and the
// language, then decides which screens are reachable. Signed out => only
// the login screen; signed in => the (app) area starting at the landing page.

import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { Loading } from "../components/ui";
import { I18nProvider } from "../i18n";
import { SessionProvider, useSession } from "../lib/session";

function RootNavigator() {
  const { loading, user } = useSession();

  // Still checking the tokens stored on the phone.
  if (loading) return <Loading />;

  return (
    <Stack screenOptions={{ headerShown: false }}>
      {/* Protected routes: Expo Router sends the user to the other group
          automatically when the login state flips. */}
      <Stack.Protected guard={user !== null}>
        <Stack.Screen name="(app)" />
      </Stack.Protected>
      <Stack.Protected guard={user === null}>
        <Stack.Screen name="login" />
      </Stack.Protected>
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <SessionProvider>
      <I18nProvider>
        <StatusBar style="auto" />
        <RootNavigator />
      </I18nProvider>
    </SessionProvider>
  );
}
