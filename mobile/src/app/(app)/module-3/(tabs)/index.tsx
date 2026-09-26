// The "Akties" tab — the screen the module opens on (it is the index route).
// It lists the intervention requests. By default it shows
// only the open ones (like the web screen's "Open Interventies" filter);
// chips switch to all requests or to one specific status, and the search
// box filters across the main text fields. Sorted by "Voorkeur Levering",
// oldest first, and grouped per day under a "Maandag 02/07/2026" header. Tap a request to view/edit it;
// the "+" button (only for users allowed to create) starts a new one.

import { Feather } from "@expo/vector-icons";
import { Redirect, useFocusEffect, useRouter } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import { Pressable, ScrollView, SectionList, StyleSheet, Text, TextInput, View, useColorScheme } from "react-native";

import { formatDeliveryDate, formatTime, teamLabel, wallClockKey } from "../../../../components/module-3/format";
import { useModule3Permissions } from "../../../../components/module-3/module-3-context";
import { StatusPill } from "../../../../components/module-3/status-pill";
import { Card, ErrorView, Loading } from "../../../../components/ui";
import { useI18n } from "../../../../i18n";
import { module3Api } from "../../../../lib/module-api";
import { getModuleTheme } from "../../../../lib/module-theme";
import { useColors } from "../../../../lib/theme";
import type { InterventionRequest } from "../../../../lib/types";
import { useAsync } from "../../../../lib/use-async";

// Which requests the list shows: only open ones, all, or one status (its id).
type Filter = "open" | "all" | number;

// Users whose role may not view requests have no Akties tab: send them to
// the KPI tab instead of an empty list. Checked in a wrapper so the list's
// hooks below always run in the same order.
export default function ActionsTab() {
  const permissions = useModule3Permissions();
  if (!permissions.can_view_requests) return <Redirect href="/module-3/kpi" />;
  return <ActionsScreen />;
}

function ActionsScreen() {
  const { t, language } = useI18n();
  const colors = useColors();
  const isDark = useColorScheme() === "dark";
  const router = useRouter();
  const permissions = useModule3Permissions();
  const accent = getModuleTheme("module-3").tileColor;

  const [filter, setFilter] = useState<Filter>("open");
  const [search, setSearch] = useState("");

  // Requests and the dropdown lists (statuses, teams) come together.
  const { data, error, loading, refreshing, reload } = useAsync(
    async () => {
      const [requests, lookups] = await Promise.all([module3Api.listRequests(), module3Api.lookups()]);
      return { requests, lookups };
    },
    // Reloaded on every focus instead: coming back from an edit shows the change.
    { autoLoad: false },
  );
  useFocusEffect(
    useCallback(() => {
      void reload();
    }, [reload]),
  );

  const lookups = data?.lookups ?? null;
  const statusById = useMemo(() => new Map((lookups?.statuses ?? []).map((status) => [status.id, status])), [lookups]);

  // Apply the status filter, then the search text, then sort.
  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const filtered = (data?.requests ?? []).filter((request) => {
      const status = statusById.get(request.status_id);
      if (filter === "open" && !(status?.is_open ?? true)) return false;
      if (typeof filter === "number" && request.status_id !== filter) return false;
      if (needle === "") return true;
      const haystack = [
        request.request_number,
        teamLabel(request, lookups),
        request.question,
        request.employee_name,
        request.delivery_location,
        request.zone,
        request.cart_number,
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
    // Oldest "Voorkeur Levering" on top; requests without one at the bottom;
    // same date → by request number so the order never jumps around. Sorted
    // on the wall-clock digits, exactly like the web (see format.ts).
    return filtered.sort((a, b) => {
      if (!a.preferred_delivery_at || !b.preferred_delivery_at) {
        if (a.preferred_delivery_at) return -1;
        if (b.preferred_delivery_at) return 1;
      } else {
        const byDate = wallClockKey(a.preferred_delivery_at).localeCompare(wallClockKey(b.preferred_delivery_at));
        if (byDate !== 0) return byDate;
      }
      return a.request_number.localeCompare(b.request_number);
    });
  }, [data, filter, search, statusById, lookups]);

  // Group the sorted list into one section per "Voorkeur Levering" day. The
  // list is already sorted, so a day's requests are always next to each other;
  // requests without a date form the last section.
  const sections = useMemo(() => {
    const result: { title: string; data: InterventionRequest[] }[] = [];
    for (const request of visible) {
      const title =
        formatDeliveryDate(request.preferred_delivery_at, language) || t("interventionRequests.requests.noDeliveryDate");
      const last = result[result.length - 1];
      if (last && last.title === title) last.data.push(request);
      else result.push({ title, data: [request] });
    }
    return result;
  }, [visible, language, t]);

  if (loading) return <Loading />;
  if (error || data === null) return <ErrorView error={error ?? new Error("No data")} onRetry={reload} />;

  const chips: { key: string; label: string; value: Filter }[] = [
    { key: "open", label: t("interventionRequests.requests.filterOpen"), value: "open" },
    { key: "all", label: t("interventionRequests.requests.filterAll"), value: "all" },
    ...data.lookups.statuses.map((status) => ({ key: `status-${status.id}`, label: status.name, value: status.id as Filter })),
  ];

  function renderItem({ item }: { item: InterventionRequest }) {
    const status = statusById.get(item.status_id);
    return (
      <Pressable onPress={() => router.push(`/module-3/request/${item.id}`)}>
        <Card style={styles.item}>
          <View style={styles.itemTop}>
            <Text style={[styles.number, { color: colors.text }]}>{item.request_number}</Text>
            {status && <StatusPill name={status.name} color={status.color} />}
          </View>
          <Text style={[styles.team, { color: colors.text }]} numberOfLines={1}>
            {teamLabel(item, lookups)}
          </Text>
          <Text style={{ color: colors.muted }} numberOfLines={2}>
            {item.question}
          </Text>
          {/* The day is already in the section header; here the time + location. */}
          {(item.preferred_delivery_at || item.delivery_location) && (
            <Text style={[styles.small, { color: colors.muted }]} numberOfLines={1}>
              {[formatTime(item.preferred_delivery_at), item.delivery_location].filter(Boolean).join(" · ")}
            </Text>
          )}
        </Card>
      </Pressable>
    );
  }

  return (
    <View style={[styles.screen, { backgroundColor: colors.background }]}>
      <SectionList
        sections={sections}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderItem}
        // The day header stays pinned while scrolling through its requests;
        // opaque background so cards don't show through it.
        stickySectionHeadersEnabled
        renderSectionHeader={({ section }) => (
          <Text style={[styles.sectionHeader, { color: accent, backgroundColor: colors.background }]}>{section.title}</Text>
        )}
        onRefresh={reload}
        refreshing={refreshing}
        contentContainerStyle={styles.list}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <View style={styles.header}>
            <TextInput
              value={search}
              onChangeText={setSearch}
              placeholder={t("interventionRequests.requests.searchPlaceholder")}
              placeholderTextColor={colors.muted}
              autoCorrect={false}
              style={[styles.search, { color: colors.text, borderColor: colors.border, backgroundColor: colors.inputBackground }]}
            />
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
              {chips.map((chip) => {
                const selected = chip.value === filter;
                return (
                  <Pressable
                    key={chip.key}
                    onPress={() => setFilter(chip.value)}
                    style={[styles.chip, { borderColor: selected ? accent : colors.border, backgroundColor: selected ? accent : "transparent" }]}
                  >
                    <Text style={{ color: selected ? "#ffffff" : colors.text, fontWeight: "600" }}>{chip.label}</Text>
                  </Pressable>
                );
              })}
            </ScrollView>
          </View>
        }
        ListEmptyComponent={
          <Text style={[styles.empty, { color: colors.muted }]}>
            {t("interventionRequests.requests.noResults")}
          </Text>
        }
      />

      {/* "+" only for users whose web role allows creating requests. */}
      {permissions.can_create_requests && (
        <Pressable
          onPress={() => router.push("/module-3/request/new")}
          accessibilityLabel={t("interventionRequests.requests.newRequest")}
          style={[styles.fab, { backgroundColor: accent }]}
        >
          <Feather name="plus" size={28} color="#ffffff" />
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  list: { padding: 16, gap: 12, paddingBottom: 96 },
  header: { gap: 12, marginBottom: 4 },
  search: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16 },
  chips: { gap: 8 },
  chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8 },
  item: { gap: 6 },
  itemTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  number: { fontSize: 16, fontWeight: "700" },
  team: { fontSize: 15, fontWeight: "600" },
  small: { fontSize: 13 },
  sectionHeader: { fontSize: 16, fontWeight: "700", paddingTop: 8, paddingBottom: 4 },
  empty: { textAlign: "center", paddingVertical: 32 },
  fab: {
    position: "absolute",
    right: 20,
    bottom: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: "center",
    justifyContent: "center",
    elevation: 4,
    shadowColor: "#000",
    shadowOpacity: 0.25,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 3 },
  },
});
