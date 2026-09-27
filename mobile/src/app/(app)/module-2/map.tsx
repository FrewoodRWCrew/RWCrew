// KarTracker's "Kar Map" on the phone: Karren, Afleverlocaties and
// Distributiepunten with a known location as coloured pins on a map (the
// same colours and popups as the web's kar-map.tsx), a chip per layer to
// show/hide it, the ground plans overlaid (on/off chip), and a search box
// that lists matches and flies to the one tapped. Opening it from Kar
// Planning's "Toon op kaart" (?focus=kar-<id>) flies straight to that kar.

import { Feather } from "@expo/vector-icons";
import { useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { FlatList, Keyboard, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { LeafletMap, type GroundplanOverlay, type MapPin } from "../../../components/module-2/leaflet-map";
import { ErrorView, Loading } from "../../../components/ui";
import { useT } from "../../../i18n";
import { module2Api } from "../../../lib/module-api";
import type { KarMapData } from "../../../lib/types";
import { useColors } from "../../../lib/theme";
import { useAsync } from "../../../lib/use-async";

type LayerKey = "kar" | "afleverlocatie" | "distributiepunt";

// Karren use this module's own purple; the other two layers the web's
// emerald-600 / amber-600, so all three read apart at a glance.
const LAYER_COLORS: Record<LayerKey, string> = {
  kar: "#9333ea",
  afleverlocatie: "#059669",
  distributiepunt: "#d97706",
};

// One searchable row of the map, located or not.
type MapRow = {
  layer: LayerKey;
  key: string;
  name: string;
  details: string;
  popupHtml: string;
  latitude: number | null;
  longitude: number | null;
};

// Popups are HTML inside the WebView: escape every value that goes in.
function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// A popup of labelled lines, e.g. "Kar nr: B001".
function labelledPopup(lines: [string, string][]): string {
  return lines.map(([label, value]) => `<b>${escapeHtml(label)}:</b> ${escapeHtml(value)}`).join("<br/>");
}

function textMatches(fieldValue: string, filterValue: string): boolean {
  return fieldValue.toLowerCase().includes(filterValue.toLowerCase());
}

export default function KarMapScreen() {
  const t = useT();
  const colors = useColors();
  const { focus: focusParam } = useLocalSearchParams<{ focus?: string }>();

  // The pins, and the ground plans (list first, their images afterwards).
  const { data, error, loading, reload } = useAsync(async () => {
    const [mapData, groundplans] = await Promise.all([module2Api.karMap(), module2Api.groundplans()]);
    return { mapData, groundplans };
  });

  const [overlays, setOverlays] = useState<GroundplanOverlay[]>([]);
  const groundplanList = data?.groundplans;
  // The images are fetched with the login token and handed to the map as
  // data: URIs; a failing image simply isn't shown.
  useEffect(() => {
    if (!groundplanList || groundplanList.length === 0) return;
    let cancelled = false;
    void Promise.all(
      groundplanList.map(async (plan): Promise<GroundplanOverlay | null> => {
        try {
          return {
            key: plan.id,
            uri: await module2Api.groundplanImage(plan.id),
            bounds: [
              [plan.sw_latitude, plan.sw_longitude],
              [plan.ne_latitude, plan.ne_longitude],
            ],
          };
        } catch {
          return null;
        }
      }),
    ).then((loaded) => {
      if (!cancelled) setOverlays(loaded.filter((overlay): overlay is GroundplanOverlay => overlay !== null));
    });
    return () => {
      cancelled = true;
    };
  }, [groundplanList]);

  // Which layers are shown; the ground plans start visible when there are any.
  const [visible, setVisible] = useState<Record<LayerKey, boolean>>({
    kar: true,
    afleverlocatie: true,
    distributiepunt: true,
  });
  const [showGroundplan, setShowGroundplan] = useState(true);
  const [search, setSearch] = useState("");
  // The pin to fly to: Kar Planning's ?focus first, later a tapped search match.
  const [focus, setFocus] = useState<{ key: string; token: number } | null>(
    focusParam ? { key: focusParam, token: 1 } : null,
  );

  // Every row of the three layers, with its popup, like the web.
  const rows = useMemo<MapRow[]>(() => (data ? buildRows(data.mapData, t) : []), [data, t]);

  // The rows of the shown layers that match the search.
  const visibleRows = useMemo(
    () =>
      rows.filter(
        (row) => visible[row.layer] && (!search || textMatches(row.name, search) || textMatches(row.details, search)),
      ),
    [rows, visible, search],
  );

  // Only rows with coordinates become pins.
  const pins = useMemo<MapPin[]>(
    () =>
      visibleRows
        .filter((row) => row.latitude !== null && row.longitude !== null)
        .map((row) => ({
          key: row.key,
          latitude: row.latitude as number,
          longitude: row.longitude as number,
          color: LAYER_COLORS[row.layer],
          popupHtml: row.popupHtml,
        })),
    [visibleRows],
  );

  // Like the web: when the search narrows it down to exactly one located
  // pin, fly there without an extra tap.
  function handleSearchChange(value: string) {
    setSearch(value);
    if (!value) return;
    const located = rows.filter(
      (row) =>
        visible[row.layer] &&
        (textMatches(row.name, value) || textMatches(row.details, value)) &&
        row.latitude !== null,
    );
    if (located.length === 1) setFocus((current) => ({ key: located[0].key, token: (current?.token ?? 0) + 1 }));
  }

  // A tapped match: close the list (all pins come back) and fly there.
  function locate(row: MapRow) {
    if (row.latitude === null) return;
    Keyboard.dismiss();
    setSearch("");
    setFocus((current) => ({ key: row.key, token: (current?.token ?? 0) + 1 }));
  }

  if (loading) return <Loading />;
  if (error || data === null) return <ErrorView error={error ?? new Error("No data")} onRetry={reload} />;

  const hasGroundplans = data.groundplans.length > 0;
  const layerChips: { key: LayerKey; label: string }[] = [
    { key: "kar", label: t("karTracker.map.layerKarren") },
    { key: "afleverlocatie", label: t("karTracker.map.layerAfleverlocaties") },
    { key: "distributiepunt", label: t("karTracker.map.layerDistributiepunten") },
  ];

  return (
    <View style={styles.container}>
      {/* Controls: search box and one chip per layer. */}
      <View style={[styles.controls, { backgroundColor: colors.background, borderColor: colors.border }]}>
        <TextInput
          value={search}
          onChangeText={handleSearchChange}
          placeholder={t("karTracker.map.searchPlaceholder")}
          placeholderTextColor={colors.muted}
          autoCorrect={false}
          autoCapitalize="none"
          clearButtonMode="while-editing"
          style={[styles.search, { color: colors.text, borderColor: colors.border, backgroundColor: colors.inputBackground }]}
        />
        <View style={styles.chips}>
          {layerChips.map((chip) => (
            <Chip
              key={chip.key}
              label={chip.label}
              color={LAYER_COLORS[chip.key]}
              active={visible[chip.key]}
              onPress={() => setVisible((current) => ({ ...current, [chip.key]: !current[chip.key] }))}
            />
          ))}
          {hasGroundplans && (
            <Chip
              label={t("karTracker.map.layerGroundplan")}
              color={colors.muted}
              active={showGroundplan}
              onPress={() => setShowGroundplan((current) => !current)}
            />
          )}
        </View>
      </View>

      <View style={styles.mapArea}>
        <LeafletMap pins={pins} groundplans={overlays} showGroundplan={showGroundplan} focus={focus} />

        {/* While searching: the matches over the map, tap one to fly there. */}
        {search.length > 0 && (
          <View style={[styles.results, { backgroundColor: colors.background, borderColor: colors.border }]}>
            <FlatList
              data={visibleRows}
              keyExtractor={(row) => row.key}
              keyboardShouldPersistTaps="handled"
              ListEmptyComponent={
                <Text style={[styles.resultEmpty, { color: colors.muted }]}>{t("karTracker.map.noMatches")}</Text>
              }
              renderItem={({ item }) => (
                <Pressable
                  onPress={() => locate(item)}
                  disabled={item.latitude === null}
                  style={[styles.result, { borderColor: colors.border }]}
                >
                  <View style={[styles.dot, { backgroundColor: LAYER_COLORS[item.layer] }]} />
                  <View style={styles.resultText}>
                    <Text style={[styles.resultName, { color: colors.text }]}>{item.name}</Text>
                    <Text style={{ color: colors.muted }} numberOfLines={1}>
                      {item.latitude === null ? t("karTracker.map.noCoordinates") : item.details}
                    </Text>
                  </View>
                  {item.latitude !== null && <Feather name="crosshair" size={18} color={colors.muted} />}
                </Pressable>
              )}
            />
          </View>
        )}
      </View>
    </View>
  );
}

// Turn the backend's three lists into map rows with the web's popup fields.
function buildRows(mapData: KarMapData, t: ReturnType<typeof useT>): MapRow[] {
  const karren: MapRow[] = mapData.karren.map((kar) => ({
    layer: "kar",
    key: `kar-${kar.id}`,
    name: kar.kar_nummer,
    details: `${kar.status_name} • ${kar.team_name ?? t("karTracker.noTeam")}`,
    popupHtml: labelledPopup([
      [t("karTracker.map.popupKarNummer"), kar.kar_nummer],
      [t("karTracker.map.popupStatus"), kar.status_name],
      [t("karTracker.map.popupPloeg"), kar.team_name ?? t("karTracker.noTeam")],
    ]),
    latitude: kar.latitude,
    longitude: kar.longitude,
  }));
  const afleverlocaties: MapRow[] = mapData.afleverlocaties.map((location) => ({
    layer: "afleverlocatie",
    key: `afleverlocatie-${location.id}`,
    name: location.name,
    details: `${location.zone_name} • ${location.distributiepunt_name}`,
    popupHtml: labelledPopup([
      [t("karTracker.map.popupOmschrijving"), location.description ?? t("karTracker.map.noDescription")],
      [t("karTracker.map.popupNaam"), location.name],
      [t("karTracker.map.popupZone"), location.zone_name],
    ]),
    latitude: location.latitude,
    longitude: location.longitude,
  }));
  const distributiepunten: MapRow[] = mapData.distributiepunten.map((point) => ({
    layer: "distributiepunt",
    key: `distributiepunt-${point.id}`,
    name: point.name,
    details: point.terrein_positie ?? t("karTracker.map.noTerreinPositie"),
    // Name in bold, then its site position, like the web popup.
    popupHtml: `<b>${escapeHtml(point.name)}</b><br/>${escapeHtml(point.terrein_positie ?? t("karTracker.map.noTerreinPositie"))}`,
    latitude: point.latitude,
    longitude: point.longitude,
  }));
  return [...karren, ...afleverlocaties, ...distributiepunten];
}

type ChipProps = { label: string; color: string; active: boolean; onPress: () => void };

// A layer on/off switch: coloured dot + name, filled while the layer is shown.
function Chip({ label, color, active, onPress }: ChipProps) {
  const colors = useColors();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="switch"
      accessibilityState={{ checked: active }}
      style={[
        styles.chip,
        { borderColor: active ? color : colors.border, backgroundColor: active ? colors.card : "transparent" },
      ]}
    >
      <View style={[styles.dot, { backgroundColor: active ? color : colors.border }]} />
      <Text style={[styles.chipText, { color: active ? colors.text : colors.muted }]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  controls: { padding: 12, gap: 8, borderBottomWidth: StyleSheet.hairlineWidth },
  search: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8, fontSize: 16 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 6 },
  chip: { flexDirection: "row", alignItems: "center", gap: 6, borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5 },
  chipText: { fontSize: 13, fontWeight: "600" },
  dot: { width: 12, height: 12, borderRadius: 6 },
  mapArea: { flex: 1 },
  results: { position: "absolute", top: 0, left: 0, right: 0, maxHeight: "50%", borderBottomWidth: 1 },
  result: { flexDirection: "row", alignItems: "center", gap: 10, paddingHorizontal: 14, paddingVertical: 10, borderBottomWidth: StyleSheet.hairlineWidth },
  resultText: { flex: 1 },
  resultName: { fontSize: 15, fontWeight: "600" },
  resultEmpty: { padding: 14 },
});
