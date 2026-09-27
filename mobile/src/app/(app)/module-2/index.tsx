// KarTracker's home screen on the phone: the phone version of the web
// module's left-hand menu (kartracker-sidebar.tsx). Same groups and order as
// the web, but only the screens the phone supports, each shown only when the
// user's KarTracker role may view it. So far: "Acties" > KarScan (the web's
// "Manuele kar beweging"), Kar Planning and Kar Map.

import { Feather } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { useModule2Permissions } from "../../../components/module-2/module-2-context";
import { Centered } from "../../../components/ui";
import { useT } from "../../../i18n";
import { getModuleTheme } from "../../../lib/module-theme";
import type { FeatherIconName } from "../../../lib/module-theme";
import { useColors } from "../../../lib/theme";

export default function KarTrackerHomeScreen() {
  const t = useT();
  const router = useRouter();
  const colors = useColors();
  const permissions = useModule2Permissions();

  // No screen this user may open on the phone: say so instead of an empty menu.
  if (!permissions.can_view_actions && !permissions.can_view_karplanning && !permissions.can_view_karmap) {
    return (
      <Centered>
        <Text style={[styles.message, { color: colors.text }]}>{t("karTracker.noScreens")}</Text>
      </Centered>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.content}>
      {/* "Acties" group, with the same lightning icon as the web sidebar. */}
      <View style={styles.groupHeader}>
        <Feather name="zap" size={16} color={colors.muted} />
        <Text style={[styles.groupTitle, { color: colors.muted }]}>{t("karTracker.actionsGroup")}</Text>
      </View>

      {/* Same order as the web sidebar: Manuele kar beweging, Kar Planning, Kar Map. */}
      {permissions.can_view_actions && (
        <MenuItem
          icon="maximize"
          title={t("karScan.moduleTitle")}
          description={t("karScan.menuDescription")}
          onPress={() => router.push("/module-2/scan")}
        />
      )}
      {permissions.can_view_karplanning && (
        <MenuItem
          icon="list"
          title={t("karTracker.planning.title")}
          description={t("karTracker.planning.menuDescription")}
          onPress={() => router.push("/module-2/planning")}
        />
      )}
      {permissions.can_view_karmap && (
        <MenuItem
          icon="map"
          title={t("karTracker.map.title")}
          description={t("karTracker.map.menuDescription")}
          onPress={() => router.push("/module-2/map")}
        />
      )}
    </ScrollView>
  );
}

type MenuItemProps = {
  icon: FeatherIconName;
  title: string;
  description: string;
  onPress: () => void;
};

// One screen in the menu: a purple icon, its name and a one-line explanation.
function MenuItem({ icon, title, description, onPress }: MenuItemProps) {
  const colors = useColors();
  const theme = getModuleTheme("module-2");

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [styles.item, { backgroundColor: colors.card }, pressed && styles.pressed]}
    >
      <View style={[styles.itemIcon, { backgroundColor: theme.tileColor }]}>
        <Feather name={icon} size={22} color={theme.onTileColor} />
      </View>
      <View style={styles.itemText}>
        <Text style={[styles.itemTitle, { color: colors.text }]}>{title}</Text>
        <Text style={{ color: colors.muted }}>{description}</Text>
      </View>
      <Feather name="chevron-right" size={22} color={colors.muted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { padding: 16, gap: 8 },
  message: { fontSize: 16, textAlign: "center" },
  groupHeader: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 4, paddingBottom: 4 },
  groupTitle: { fontSize: 12, fontWeight: "700", letterSpacing: 0.8, textTransform: "uppercase" },
  item: { flexDirection: "row", alignItems: "center", gap: 12, borderRadius: 12, padding: 12 },
  pressed: { opacity: 0.85 },
  itemIcon: { width: 44, height: 44, borderRadius: 10, alignItems: "center", justifyContent: "center" },
  itemText: { flex: 1, gap: 2 },
  itemTitle: { fontSize: 16, fontWeight: "700" },
});
