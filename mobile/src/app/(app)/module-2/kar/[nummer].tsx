// KarScan's movement form for one scanned kar: the kar and its team
// (read-only), its new status (pre-selected with the current one), and the
// phone's GPS position, taken automatically when the form opens. Saving logs
// the movement exactly like the web's "Manuele kar beweging" and goes back to
// the scanner for the next kar. Below: the kar's last few movements.

import * as Location from "expo-location";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import { Alert, ScrollView, StyleSheet, Text, View } from "react-native";

import { useModule2Permissions } from "../../../../components/module-2/module-2-context";
import { RecentActions } from "../../../../components/module-2/recent-actions";
import { SelectField } from "../../../../components/select-field";
import { Button, Card, ErrorView, Loading, describeError } from "../../../../components/ui";
import { useT } from "../../../../i18n";
import { module2Api } from "../../../../lib/module-api";
import { getModuleTheme } from "../../../../lib/module-theme";
import { useColors } from "../../../../lib/theme";
import { useAsync } from "../../../../lib/use-async";

type Position = { latitude: number; longitude: number; accuracy: number | null };

// The outcome of one attempt to read the phone's position.
type FixResult = { position: Position } | { error: "denied" | "timeout" | "failed" };

// How long to wait for a GPS fix before giving up (the web's
// "Use my location" waits the same 15 seconds). Without a limit the phone
// can keep searching forever (e.g. indoors), leaving the form stuck.
const GPS_TIMEOUT_MS = 15000;

// Resolves with `fallback` when `promise` hasn't settled within `ms`.
function withTimeout<T>(promise: Promise<T>, ms: number, fallback: T): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<T>((resolve) => {
    timer = setTimeout(() => resolve(fallback), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}

// Ask for location access (the phone only asks the first time) and take a
// fresh, high-accuracy position fix, giving up after GPS_TIMEOUT_MS.
async function readPosition(): Promise<FixResult> {
  try {
    const { granted } = await Location.requestForegroundPermissionsAsync();
    if (!granted) return { error: "denied" };
    const fix = await withTimeout(
      Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
      GPS_TIMEOUT_MS,
      null,
    );
    if (fix === null) return { error: "timeout" };
    return {
      position: { latitude: fix.coords.latitude, longitude: fix.coords.longitude, accuracy: fix.coords.accuracy },
    };
  } catch {
    return { error: "failed" };
  }
}

// Coordinates are shown with 6 decimals (about 10 cm), like on the web.
function formatCoordinate(value: number): string {
  return value.toFixed(6);
}

export default function KarMovementScreen() {
  const t = useT();
  const router = useRouter();
  const colors = useColors();
  const theme = getModuleTheme("module-2");
  const permissions = useModule2Permissions();
  const { nummer } = useLocalSearchParams<{ nummer: string }>();

  // The kar (with its recent movements) and the status list, in one go.
  const { data, error, loading, reload } = useAsync(async () => {
    const [scan, statuses] = await Promise.all([module2Api.karByNummer(nummer), module2Api.statuses()]);
    return { scan, statuses };
  });

  // The chosen status: the kar's current one until the user picks the
  // status after the movement.
  const [pickedStatusId, setPickedStatusId] = useState<number | null>(null);
  const statusId = pickedStatusId ?? data?.scan.kar.status_id ?? null;

  // The GPS fix and its state. View-only users can't save a movement, so
  // their position is never taken; everyone else starts out "locating".
  const canCreate = permissions.can_create_actions;
  const [position, setPosition] = useState<Position | null>(null);
  const [locating, setLocating] = useState(canCreate);
  const [gpsError, setGpsError] = useState<string | null>(null);

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Show the outcome of a GPS attempt: the new position, or why there is none.
  const applyFix = useCallback(
    (result: FixResult) => {
      if ("position" in result) {
        setPosition(result.position);
        setGpsError(null);
      } else {
        setGpsError(
          result.error === "denied"
            ? t("karScan.gpsDenied")
            : result.error === "timeout"
              ? t("karScan.gpsTimeout")
              : t("karScan.gpsFailed"),
        );
      }
      setLocating(false);
    },
    [t],
  );

  // The position is taken automatically as soon as the form opens. A fix
  // arriving after the user left the screen is ignored.
  useEffect(() => {
    if (!canCreate) return;
    let cancelled = false;
    void readPosition().then((result) => {
      if (!cancelled) applyFix(result);
    });
    return () => {
      cancelled = true;
    };
  }, [applyFix, canCreate]);

  // "Determine location again".
  function handleRefreshLocation() {
    setLocating(true);
    setGpsError(null);
    void readPosition().then(applyFix);
  }

  async function handleSave() {
    if (!data || statusId === null || position === null) return;
    setSaving(true);
    setSaveError(null);
    try {
      const saved = await module2Api.createAction({
        kar_id: data.scan.kar.id,
        status_id: statusId,
        latitude: position.latitude,
        longitude: position.longitude,
      });
      // Confirm, and straight back to the scanner for the next kar.
      Alert.alert(t("karScan.moduleTitle"), t("karScan.saveSuccess", { kar: saved.kar_nummer }));
      router.back();
    } catch (caught) {
      setSaveError(`${t("karScan.saveError")} ${describeError(caught, t)}`);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Loading />;
  if (error || data === null) return <ErrorView error={error ?? new Error("No data")} onRetry={reload} />;

  const { kar, recent_actions: recentActions } = data.scan;
  const canSave = statusId !== null && position !== null && !saving && !locating;

  return (
    <>
      <Stack.Screen options={{ title: t("karScan.formTitle", { kar: kar.kar_nummer }) }} />
      <ScrollView contentContainerStyle={styles.content}>
        {/* The scanned kar and its team, read-only (the team is logged as-is). */}
        <Card style={styles.card}>
          <Text style={[styles.label, { color: colors.muted }]}>{t("karScan.karLabel")}</Text>
          <Text style={[styles.karNummer, { color: colors.text }]}>{kar.kar_nummer}</Text>
          <Text style={[styles.label, { color: colors.muted }]}>{t("karScan.teamLabel")}</Text>
          <Text style={[styles.value, { color: kar.team_name ? colors.text : colors.muted }]}>
            {kar.team_name ?? t("karScan.noTeam")}
          </Text>
        </Card>

        {permissions.can_create_actions ? (
          <>
            {/* The kar's status after the movement. */}
            <SelectField
              label={t("karScan.statusLabel")}
              value={statusId}
              options={data.statuses.map((karStatus) => ({ value: karStatus.id, label: karStatus.name }))}
              onChange={setPickedStatusId}
            />

            {/* The phone's GPS position, with a button to take it again. */}
            <View style={styles.field}>
              <Text style={[styles.label, { color: colors.muted }]}>{t("karScan.locationLabel")}</Text>
              {locating ? (
                <Text style={{ color: colors.muted }}>{t("karScan.locating")}</Text>
              ) : position ? (
                <Text style={[styles.value, { color: colors.text }]}>
                  {formatCoordinate(position.latitude)}, {formatCoordinate(position.longitude)}
                  {position.accuracy !== null && (
                    <Text style={{ color: colors.muted }}>
                      {"  "}
                      {t("karScan.accuracy", { meters: Math.round(position.accuracy) })}
                    </Text>
                  )}
                </Text>
              ) : null}
              {gpsError && <Text style={{ color: colors.danger }}>{gpsError}</Text>}
              <Button
                title={t("karScan.refreshLocation")}
                onPress={handleRefreshLocation}
                disabled={locating}
                color={colors.card}
                textColor={colors.text}
              />
            </View>

            {saveError && <Text style={{ color: colors.danger }}>{saveError}</Text>}
            <Button
              title={saving ? t("karScan.saving") : t("karScan.save")}
              onPress={() => void handleSave()}
              disabled={!canSave}
              color={theme.tileColor}
              textColor={theme.onTileColor}
            />
          </>
        ) : (
          <Text style={{ color: colors.muted }}>{t("karScan.noCreateRights")}</Text>
        )}

        <RecentActions actions={recentActions} />
      </ScrollView>
    </>
  );
}

const styles = StyleSheet.create({
  content: { padding: 16, gap: 16 },
  card: { gap: 2 },
  field: { gap: 6 },
  label: { fontSize: 13, fontWeight: "600" },
  karNummer: { fontSize: 24, fontWeight: "700", marginBottom: 8 },
  value: { fontSize: 16 },
});
