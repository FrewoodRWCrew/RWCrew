// The building blocks of the KPI overview: a big-number stat card and a
// list of horizontal bars (used for "requests per status" and "per team").
// Plain Views instead of a chart library: no native dependency, works in
// Expo Go, and horizontal bars read better on a narrow phone screen than a
// donut chart.

import { StyleSheet, Text, View } from "react-native";

import { Card } from "../ui";
import { useColors } from "../../lib/theme";

export function StatCard({ label, value, accent }: { label: string; value: number; accent: string }) {
  const colors = useColors();
  return (
    <Card style={styles.statCard}>
      <Text style={[styles.statValue, { color: accent }]}>{value.toLocaleString()}</Text>
      <Text style={[styles.statLabel, { color: colors.muted }]} numberOfLines={2}>
        {label}
      </Text>
    </Card>
  );
}

export type BarItem = { label: string; count: number; color: string };

type BarListProps = {
  title: string;
  description: string;
  items: BarItem[];
  emptyText: string;
};

export function BarList({ title, description, items, emptyText }: BarListProps) {
  const colors = useColors();
  // The longest bar is 100% wide; the rest are relative to it.
  const max = Math.max(0, ...items.map((item) => item.count));
  const isEmpty = max === 0;

  return (
    <Card style={styles.barCard}>
      <Text style={[styles.barTitle, { color: colors.text }]}>{title}</Text>
      <Text style={[styles.barDescription, { color: colors.muted }]}>{description}</Text>

      {isEmpty ? (
        <Text style={[styles.empty, { color: colors.muted }]}>{emptyText}</Text>
      ) : (
        items.map((item) => (
          <View key={item.label} style={styles.barRow}>
            <View style={styles.barHeader}>
              <Text style={[styles.barLabel, { color: colors.text }]} numberOfLines={1}>
                {item.label}
              </Text>
              <Text style={[styles.barCount, { color: colors.text }]}>{item.count}</Text>
            </View>
            <View style={[styles.track, { backgroundColor: colors.border }]}>
              {/* A tiny minimum width keeps a count of 1 visible next to a big one. */}
              <View
                style={[styles.fill, { width: `${Math.max((item.count / max) * 100, item.count > 0 ? 3 : 0)}%`, backgroundColor: item.color }]}
              />
            </View>
          </View>
        ))
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  statCard: { flex: 1, alignItems: "center", gap: 4, paddingHorizontal: 8 },
  statValue: { fontSize: 28, fontWeight: "700" },
  statLabel: { fontSize: 12, textAlign: "center" },
  barCard: { gap: 10 },
  barTitle: { fontSize: 17, fontWeight: "700" },
  barDescription: { fontSize: 13, marginBottom: 4 },
  empty: { textAlign: "center", paddingVertical: 24 },
  barRow: { gap: 4 },
  barHeader: { flexDirection: "row", justifyContent: "space-between", gap: 8 },
  barLabel: { flex: 1, fontSize: 14 },
  barCount: { fontSize: 14, fontWeight: "600" },
  track: { height: 10, borderRadius: 5, overflow: "hidden" },
  fill: { height: 10, borderRadius: 5 },
});
