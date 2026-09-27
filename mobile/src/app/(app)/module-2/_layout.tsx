// KarTracker (module-2): its home screen (the web sidebar's groups) opens
// first; from there KarScan's QR scanner, and the movement form for the
// scanned kar on top of that. Wrapped in Module2Provider so
// every screen inside can ask what the user may do; without module access
// nothing inside is shown. Kar Map, KarManagement, MasterData and Access
// Rights of this module are web-only: not here.

import { Stack, useRouter } from "expo-router";
import { Image, Pressable } from "react-native";

import { Module2Provider } from "../../../components/module-2/module-2-context";
import { useT } from "../../../i18n";
import { getModuleTheme } from "../../../lib/module-theme";

export default function Module2Layout() {
  const t = useT();
  const router = useRouter();
  const theme = getModuleTheme("module-2");

  return (
    <Module2Provider>
      <Stack
        screenOptions={{
          // Purple header, the web tile colour of KarTracker.
          headerStyle: { backgroundColor: theme.tileColor },
          headerTintColor: theme.onTileColor,
          headerTitleStyle: { fontWeight: "700" },
          headerBackButtonDisplayMode: "minimal",
        }}
      >
        <Stack.Screen
          name="index"
          options={{
            title: t("karTracker.moduleTitle"),
            // Same Altsien logo as module-3's header; tapping it returns to the landing page.
            headerLeft: () => (
              <Pressable
                onPress={() => router.navigate("/")}
                hitSlop={12}
                accessibilityRole="button"
                accessibilityLabel={t("modules.back")}
                style={{ paddingRight: 16 }}
              >
                <Image
                  source={require("../../../../assets/altsien-logo.png")}
                  style={{ width: 28, height: 33 }}
                  resizeMode="contain"
                />
              </Pressable>
            ),
          }}
        />
        <Stack.Screen name="scan" options={{ title: t("karScan.moduleTitle") }} />
        <Stack.Screen name="planning" options={{ title: t("karTracker.planning.title") }} />
        <Stack.Screen name="map" options={{ title: t("karTracker.map.title") }} />
        <Stack.Screen name="kar/[nummer]"options={{ title: t("karScan.karLabel") }} />
      </Stack>
    </Module2Provider>
  );
}
