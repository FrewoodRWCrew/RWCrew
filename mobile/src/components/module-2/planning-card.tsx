// One kar in the phone's Kar Planning list: kar number, status, ploeg and
// transport type. Tapping it unfolds the planned afleverlocatie per festival
// of the chosen season and the kar's last GPS location, with a button to see
// it on the Kar Map (when the user may open the map and the kar has a location).

import { Feather } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useT } from "../../i18n";
import { getModuleTheme } from "../../lib/module-theme";
import type { KarPlanningReport, KarPlanningRow } from "../../lib/types";
import { useColors } from "../../lib/theme";
import { Button } from "../ui";

type Props = {
  row: KarPlanningRow;
  festivals: KarPlanningReport["festivals"];
  expanded: boolean;
  onToggle: () => void;
  // Absent when the user may not open the Kar Map.
  onShowOnMap?: () => void;
};

export function PlanningCard({ row, festivals, expanded, onToggle, onShowOnMap }: Props) {
  const t = useT();
  const colors = useColors();
  const theme = getModuleTheme("module-2");

  return (
    <Pressable
      onPress={onToggle}
      accessibilityRole="button"
      accessibilityState={{ expanded }}
      style={[styles.card, { backgroundColor: colors.card }]}
    >
      {/* Always visible: kar number + status, then ploeg and transport type. */}
      <View style={styles.headerLine}>
        <Text style={[styles.karNummer, { color: colors.text }]}>{row.kar_nummer}</Text>
        <View style={[styles.statusPill, { borderColor: theme.tileColor }]}>
          <Text style={[styles.statusText, { color: colors.text }]} numberOfLines={1}>
            {row.status_name}
          </Text>
        </View>
        <Feather name={expanded ? "chevron-up" : "chevron-down"} size={20} color={colors.muted} />
      </View>
      <Text style={{ color: row.team_name ? colors.text : colors.muted }}>
        {row.team_name ?? t("karTracker.noTeam")}
      </Text>
      <Text style={{ color: colors.muted }}>
        {t("karTracker.planning.transportType")}: {row.transport_type_name}
      </Text>

      {expanded && (
        <View style={[styles.details, { borderColor: colors.border }]}>
          {/* One line per festival of the season: its planned afleverlocatie. */}
          {festivals.length === 0 ? (
            <Text style={{ color: colors.muted }}>{t("karTracker.planning.noFestivals")}</Text>
          ) : (
            festivals.map((festival) => (
              <View key={festival.id} style={styles.detailLine}>
                <Text style={[styles.detailLabel, { color: colors.muted }]}>{festival.name}</Text>
                <Text style={{ color: colors.text }}>
                  {row.afleverlocaties[String(festival.id)] ?? t("karTracker.planning.notPlanned")}
                </Text>
              </View>
            ))
          )}

          {/* The kar's last known GPS location. */}
          <View style={styles.detailLine}>
            <Text style={[styles.detailLabel, { color: colors.muted }]}>{t("karTracker.planning.geolocation")}</Text>
            <Text style={{ color: row.geolocation ? colors.text : colors.muted }}>
              {row.geolocation ?? t("karTracker.planning.noGeolocation")}
            </Text>
          </View>

          {onShowOnMap && row.geolocation && (
            <Button
              title={t("karTracker.planning.showOnMap")}
              onPress={onShowOnMap}
              color={theme.tileColor}
              textColor={theme.onTileColor}
            />
          )}
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { borderRadius: 12, padding: 14, gap: 4 },
  headerLine: { flexDirection: "row", alignItems: "center", gap: 8 },
  karNummer: { fontSize: 18, fontWeight: "700" },
  statusPill: { flexShrink: 1, borderWidth: 1, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 2, marginLeft: "auto" },
  statusText: { fontSize: 13, fontWeight: "600" },
  details: { marginTop: 8, paddingTop: 8, borderTopWidth: StyleSheet.hairlineWidth, gap: 8 },
  detailLine: { gap: 2 },
  detailLabel: { fontSize: 13, fontWeight: "600" },
});
