// KarTracker's "Kar Planning" on the phone: the web's read-only report as a
// searchable list of cards (the web table is too wide for a phone). A season
// dropdown (the open seasons, newest pre-selected) adds each kar's planned
// afleverlocatie per festival. The web's "Print" (PDF karbladen) is web-only.

import { useRouter } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { FlatList, RefreshControl, StyleSheet, Text, TextInput, View } from "react-native";

import { useModule2Permissions } from "../../../components/module-2/module-2-context";
import { PlanningCard } from "../../../components/module-2/planning-card";
import { SelectField } from "../../../components/select-field";
import { Button, ErrorView, Loading, describeError } from "../../../components/ui";
import { useT } from "../../../i18n";
import { module2Api } from "../../../lib/module-api";
import type { KarPlanningReport, KarPlanningRow } from "../../../lib/types";
import { useColors } from "../../../lib/theme";
import { useAsync } from "../../../lib/use-async";

// A report remembered together with the season it was loaded for.
type LoadedReport = { seasonId: number | null; report: KarPlanningReport };

// Whatever was thrown, as an Error.
function toError(caught: unknown): Error {
  return caught instanceof Error ? caught : new Error(String(caught));
}

// Everything a kar can be found by: number, status, ploeg, transport type,
// planned locations and GPS location.
function searchableText(row: KarPlanningRow): string {
  return [
    row.kar_nummer,
    row.status_name,
    row.team_name ?? "",
    row.transport_type_name,
    row.geolocation ?? "",
    ...Object.values(row.afleverlocaties),
  ]
    .join(" ")
    .toLowerCase();
}

export default function KarPlanningScreen() {
  const t = useT();
  const router = useRouter();
  const colors = useColors();
  const permissions = useModule2Permissions();

  // The open seasons for the dropdown.
  const seasons = useAsync(module2Api.seasons);

  // The chosen season: undefined = not chosen yet (the newest one is used),
  // null = "no season" (no festival columns).
  const [pickedSeasonId, setPickedSeasonId] = useState<number | null | undefined>(undefined);
  const seasonId = pickedSeasonId === undefined ? (seasons.data?.[0]?.id ?? null) : pickedSeasonId;

  const [loaded, setLoaded] = useState<LoadedReport | null>(null);
  // The last failed load, with the season it was for, so a failure for the
  // chosen season is shown instead of an endless spinner.
  const [loadError, setLoadError] = useState<{ seasonId: number | null; error: Error } | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // (Re)load the report once the seasons are known and whenever the season
  // changes. A response for a season that is no longer chosen is dropped.
  const seasonsReady = seasons.data !== null;
  useEffect(() => {
    if (!seasonsReady) return;
    let cancelled = false;
    module2Api
      .karPlanning(seasonId)
      .then((report) => {
        if (cancelled) return;
        setLoaded({ seasonId, report });
        setLoadError(null);
      })
      .catch((caught: unknown) => {
        if (!cancelled) setLoadError({ seasonId, error: toError(caught) });
      });
    return () => {
      cancelled = true;
    };
  }, [seasonId, seasonsReady]);

  // Pull-to-refresh and "try again": load the report for the current season again.
  async function handleRefresh() {
    setRefreshing(true);
    try {
      setLoaded({ seasonId, report: await module2Api.karPlanning(seasonId) });
      setLoadError(null);
    } catch (caught) {
      setLoadError({ seasonId, error: toError(caught) });
    } finally {
      setRefreshing(false);
    }
  }

  // The cards matching the search box.
  const rows = useMemo(() => {
    const allRows = loaded?.report.rows ?? [];
    const wanted = search.trim().toLowerCase();
    return wanted ? allRows.filter((row) => searchableText(row).includes(wanted)) : allRows;
  }, [loaded, search]);

  if (seasons.loading) return <Loading />;
  if (seasons.error) return <ErrorView error={seasons.error} onRetry={seasons.reload} />;
  // A failed load for the chosen season (an older failure for another season doesn't count).
  const currentError = loadError !== null && loadError.seasonId === seasonId ? loadError.error : null;
  // The report on screen belongs to the chosen season.
  const hasCurrentReport = loaded !== null && loaded.seasonId === seasonId;
  // Still loading the first report, or the one for a newly chosen season.
  const isLoadingReport = !hasCurrentReport && currentError === null;

  return (
    <FlatList
      data={hasCurrentReport ? rows : []}
      keyExtractor={(row) => String(row.id)}
      contentContainerStyle={styles.content}
      keyboardShouldPersistTaps="handled"
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => void handleRefresh()} />}
      ListHeaderComponent={
        <View style={styles.header}>
          {/* The season whose festivals get a planned location per kar. */}
          <SelectField
            label={t("karTracker.planning.seasonLabel")}
            value={seasonId}
            options={(seasons.data ?? []).map((season) => ({ value: season.id, label: season.name }))}
            onChange={setPickedSeasonId}
            noneLabel={t("karTracker.planning.noSeason")}
          />
          <TextInput
            value={search}
            onChangeText={setSearch}
            placeholder={t("karTracker.planning.searchPlaceholder")}
            placeholderTextColor={colors.muted}
            autoCorrect={false}
            autoCapitalize="none"
            clearButtonMode="while-editing"
            style={[styles.search, { color: colors.text, borderColor: colors.border, backgroundColor: colors.inputBackground }]}
          />
          {isLoadingReport && <Loading />}
          {/* The chosen season's report failed: say why and offer a retry;
              the season dropdown above stays usable. */}
          {currentError !== null && (
            <View style={styles.error}>
              <Text style={{ color: colors.danger }}>{describeError(currentError, t)}</Text>
              <Button title={t("common.retry")} onPress={() => void handleRefresh()} disabled={refreshing} />
            </View>
          )}
        </View>
      }
      ListEmptyComponent={
        !hasCurrentReport ? null : (
          <Text style={[styles.empty, { color: colors.muted }]}>{t("karTracker.planning.noKarren")}</Text>
        )
      }
      renderItem={({ item }) => (
        <PlanningCard
          row={item}
          festivals={loaded?.report.festivals ?? []}
          expanded={expandedId === item.id}
          onToggle={() => setExpandedId((current) => (current === item.id ? null : item.id))}
          onShowOnMap={
            permissions.can_view_karmap
              ? () => router.push({ pathname: "/module-2/map", params: { focus: `kar-${item.id}` } })
              : undefined
          }
        />
      )}
    />
  );
}

const styles = StyleSheet.create({
  content: { padding: 16, gap: 10 },
  header: { gap: 10, marginBottom: 4 },
  search: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16 },
  empty: { textAlign: "center", marginTop: 24 },
  error: { gap: 8 },
});
