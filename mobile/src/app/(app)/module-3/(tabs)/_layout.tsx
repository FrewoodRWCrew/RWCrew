// The two tabs of Intervention Requests: "KPI overzicht" and "Akties".
// The orange header has a "‹ Modules" button back to the landing page.
// MasterData and Access Rights of this module are web-only: not here.

import { Feather } from "@expo/vector-icons";
import { Tabs, useRouter } from "expo-router";
import { Pressable, Text } from "react-native";

import { useModule3Permissions } from "../../../../components/module-3/module-3-context";
import { useT } from "../../../../i18n";
import { getModuleTheme } from "../../../../lib/module-theme";

export default function Module3Tabs() {
  const t = useT();
  const router = useRouter();
  const permissions = useModule3Permissions();
  const theme = getModuleTheme("module-3");

  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: theme.tileColor },
        headerTintColor: theme.onTileColor,
        headerTitleStyle: { fontWeight: "700" },
        headerTitle: t("interventionRequests.moduleTitle"),
        tabBarActiveTintColor: theme.tileColor,
        headerLeft: () => (
          <Pressable onPress={() => router.navigate("/")} hitSlop={12} style={{ paddingHorizontal: 16 }}>
            <Text style={{ color: theme.onTileColor, fontSize: 16, fontWeight: "600" }}>‹ {t("modules.back")}</Text>
          </Pressable>
        ),
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: t("interventionRequests.kpiTab"),
          tabBarIcon: ({ color, size }) => <Feather name="bar-chart-2" color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="actions"
        options={{
          title: t("interventionRequests.actionsTab"),
          // Users who may not view requests don't get the tab at all.
          href: permissions.can_view_requests ? undefined : null,
          tabBarIcon: ({ color, size }) => <Feather name="zap" color={color} size={size} />,
        }}
      />
    </Tabs>
  );
}
