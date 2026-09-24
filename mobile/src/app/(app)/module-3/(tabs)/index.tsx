// The "KPI overzicht" tab: the same numbers as the web KPI overview —
// total / open / closed requests, requests per status, requests per team.

import { RefreshControl, ScrollView, StyleSheet, View, useColorScheme } from "react-native";

import { BarList, StatCard } from "../../../../components/module-3/kpi-widgets";
import { ErrorView, Loading } from "../../../../components/ui";
import { useT } from "../../../../i18n";
import { module3Api } from "../../../../lib/module-api";
import { getModuleTheme } from "../../../../lib/module-theme";
import { statusColor } from "../../../../lib/status-colors";
import { useColors } from "../../../../lib/theme";
import { useAsync } from "../../../../lib/use-async";

export default function KpiScreen() {
  const t = useT();
  const colors = useColors();
  const isDark = useColorScheme() === "dark";
  const accent = getModuleTheme("module-3").tileColor;
  const { data, error, loading, refreshing, reload } = useAsync(module3Api.dashboard);

  if (loading) return <Loading />;
  if (error || data === null) return <ErrorView error={error ?? new Error("No data")} onRetry={reload} />;

  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={reload} />}
    >
      <View style={styles.stats}>
        <StatCard label={t("interventionRequests.landing.statTotalRequests")} value={data.total_requests} accent={accent} />
        <StatCard label={t("interventionRequests.landing.statOpenRequests")} value={data.open_requests} accent={accent} />
        <StatCard label={t("interventionRequests.landing.statClosedRequests")} value={data.closed_requests} accent={accent} />
      </View>

      <BarList
        title={t("interventionRequests.landing.chartStatusTitle")}
        description={t("interventionRequests.landing.chartStatusDescription")}
        emptyText={t("interventionRequests.landing.chartEmpty")}
        // Each status keeps the colour an admin gave it on the web.
        items={data.status_breakdown.map((item) => ({
          label: item.status_name,
          count: item.count,
          color: statusColor(item.color, isDark),
        }))}
      />
      <BarList
        title={t("interventionRequests.landing.chartTeamTitle")}
        description={t("interventionRequests.landing.chartTeamDescription")}
        emptyText={t("interventionRequests.landing.chartEmpty")}
        items={data.team_breakdown.map((item) => ({ label: item.team_name, count: item.count, color: accent }))}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: 16, gap: 16 },
  stats: { flexDirection: "row", gap: 12 },
});
