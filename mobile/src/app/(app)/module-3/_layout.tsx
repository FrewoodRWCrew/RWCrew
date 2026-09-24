// The Intervention Requests area: a bottom-tab screen group ("KPI overzicht"
// and "Akties") plus the create / edit screens that open on top of it.
// Wrapped in Module3Provider so every screen inside can ask what the user
// may do; without module access nothing inside is shown.

import { Stack } from "expo-router";

import { Module3Provider } from "../../../components/module-3/module-3-context";
import { useT } from "../../../i18n";
import { getModuleTheme } from "../../../lib/module-theme";

export default function Module3Layout() {
  const t = useT();
  const theme = getModuleTheme("module-3");

  return (
    <Module3Provider>
      <Stack
        screenOptions={{
          // Same orange header as the tabs, so the module feels like one piece.
          headerStyle: { backgroundColor: theme.tileColor },
          headerTintColor: theme.onTileColor,
          headerTitleStyle: { fontWeight: "700" },
          headerBackButtonDisplayMode: "minimal",
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="request/new" options={{ title: t("interventionRequests.requests.createTitle") }} />
        <Stack.Screen name="request/[id]" options={{ title: t("interventionRequests.requests.viewTitle") }} />
      </Stack>
    </Module3Provider>
  );
}
