// A small rounded label showing a request's status in that status's own
// colour (the colour an admin picked on the web).

import { StyleSheet, Text, View } from "react-native";
import { useColorScheme } from "react-native";

import { statusColor } from "../../lib/status-colors";

export function StatusPill({ name, color }: { name: string; color: string }) {
  const isDark = useColorScheme() === "dark";
  const tint = statusColor(color, isDark);
  return (
    // "22" appended to a hex colour = about 13% opacity, for the soft background.
    <View style={[styles.pill, { backgroundColor: `${tint}22` }]}>
      <View style={[styles.dot, { backgroundColor: tint }]} />
      <Text style={[styles.text, { color: tint }]} numberOfLines={1}>
        {name}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: { flexDirection: "row", alignItems: "center", gap: 6, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4, alignSelf: "flex-start" },
  dot: { width: 8, height: 8, borderRadius: 4 },
  text: { fontSize: 13, fontWeight: "600" },
});
