// One tile on the landing page: the module's solid accent colour with its
// icon and name — the phone version of the web app's ModuleTile.

import { Feather } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useT } from "../i18n";
import { getModuleTheme } from "../lib/module-theme";
import type { ModuleInfo } from "../lib/types";

type Props = {
  module: ModuleInfo;
  width: number;
  onPress: () => void;
};

export function ModuleTile({ module, width, onPress }: Props) {
  const t = useT();
  const theme = getModuleTheme(module.key);

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [
        styles.tile,
        { width, backgroundColor: theme.tileColor },
        pressed && styles.pressed,
      ]}
    >
      <View style={styles.iconArea}>
        <Feather name={theme.icon} size={72} color={theme.onTileColor} />
      </View>
      {/* The name is translated on the phone, like the web landing tile. */}
      <Text style={[styles.name, { color: theme.onTileColor }]} numberOfLines={2}>
        {t(theme.titleKey)}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  tile: { height: 150, borderRadius: 12, padding: 12 },
  pressed: { opacity: 0.85 },
  iconArea: { flex: 1, alignItems: "center", justifyContent: "center" },
  name: { textAlign: "center", fontSize: 14, fontWeight: "600" },
});
