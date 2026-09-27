// The last few logged movements of the scanned kar, newest first, below the
// KarScan form. Read-only: deleting a movement is web-only.

import { StyleSheet, Text, View } from "react-native";

import { useI18n } from "../../i18n";
import type { KarAction } from "../../lib/types";
import { useColors } from "../../lib/theme";
import { formatDateTime } from "../module-3/format";
import { Card } from "../ui";

export function RecentActions({ actions }: { actions: KarAction[] }) {
  const { t, language } = useI18n();
  const colors = useColors();

  return (
    <View style={styles.section}>
      <Text style={[styles.title, { color: colors.text }]}>{t("karScan.historyTitle")}</Text>
      {actions.length === 0 ? (
        <Text style={{ color: colors.muted }}>{t("karScan.noHistory")}</Text>
      ) : (
        actions.map((action) => (
          <Card key={action.id} style={styles.row}>
            {/* Status on the left, when on the right. */}
            <View style={styles.line}>
              <Text style={[styles.status, { color: colors.text }]}>{action.status_name}</Text>
              <Text style={{ color: colors.muted }}>{formatDateTime(action.recorded_at, language)}</Text>
            </View>
            {/* The team at that moment and who logged it. */}
            <Text style={{ color: colors.muted }}>
              {action.team_name ?? t("karScan.noTeam")}
              {action.user_name ? ` · ${t("karScan.by", { name: action.user_name })}` : ""}
            </Text>
          </Card>
        ))
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: 8 },
  title: { fontSize: 17, fontWeight: "700", textDecorationLine: "underline" },
  row: { gap: 4, paddingVertical: 12 },
  line: { flexDirection: "row", justifyContent: "space-between", gap: 8 },
  status: { fontSize: 15, fontWeight: "600", flexShrink: 1 },
});
