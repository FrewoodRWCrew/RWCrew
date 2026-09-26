// A date + time field. iOS shows the system's compact date/time control;
// Android has no combined control, so it opens the date dialog and then the
// time dialog one after the other. The value is a timezone-less wall-clock
// "2026-09-07T23:39:00" (or null when nothing is chosen), the same shape the
// web sends — see the wall-clock note in module-3/format.ts.

import DateTimePicker, { DateTimePickerAndroid, type DateTimePickerEvent } from "@react-native-community/datetimepicker";
import { Platform, Pressable, StyleSheet, Text, View } from "react-native";

import { useI18n } from "../i18n";
import { useColors } from "../lib/theme";
import { formatWallClockDateTime, parseWallClock, toWallClockIso } from "./module-3/format";

type Props = {
  label: string;
  value: string | null;
  onChange: (value: string | null) => void;
  editable?: boolean;
};

export function DateTimeField({ label, value, onChange, editable = true }: Props) {
  const { t } = useI18n();
  const colors = useColors();
  const date = value ? parseWallClock(value) : new Date();

  // Android: pick the date first, then the time, then report the combination.
  function openAndroidPicker() {
    DateTimePickerAndroid.open({
      value: date,
      mode: "date",
      onChange: (dateEvent: DateTimePickerEvent, pickedDate?: Date) => {
        if (dateEvent.type !== "set" || !pickedDate) return;
        DateTimePickerAndroid.open({
          value: pickedDate,
          mode: "time",
          is24Hour: true,
          onChange: (timeEvent: DateTimePickerEvent, pickedTime?: Date) => {
            if (timeEvent.type !== "set" || !pickedTime) return;
            const combined = new Date(pickedDate);
            combined.setHours(pickedTime.getHours(), pickedTime.getMinutes(), 0, 0);
            onChange(toWallClockIso(combined));
          },
        });
      },
    });
  }

  return (
    <View style={styles.field}>
      <Text style={[styles.label, { color: colors.muted }]}>{label}</Text>
      <View
        style={[
          styles.input,
          { borderColor: colors.border, backgroundColor: editable ? colors.inputBackground : colors.card },
        ]}
      >
        {Platform.OS === "ios" && value && editable ? (
          // iOS: the live compact control (tapping it opens the wheel).
          <DateTimePicker
            value={date}
            mode="datetime"
            display="compact"
            onChange={(_event, picked) => picked && onChange(toWallClockIso(picked))}
          />
        ) : (
          <Pressable
            disabled={!editable}
            style={styles.valueArea}
            onPress={() => (Platform.OS === "ios" ? onChange(toWallClockIso(new Date())) : openAndroidPicker())}
          >
            <Text style={{ color: value ? colors.text : colors.muted, fontSize: 16 }}>
              {value ? formatWallClockDateTime(value) : t("interventionRequests.requests.choose")}
            </Text>
          </Pressable>
        )}

        {editable && value && (
          <Pressable onPress={() => onChange(null)}>
            <Text style={[styles.clear, { color: colors.brand }]}>{t("interventionRequests.requests.clear")}</Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: 4 },
  label: { fontSize: 13, fontWeight: "600" },
  input: {
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    minHeight: 48,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  valueArea: { flex: 1, paddingVertical: 4 },
  clear: { fontSize: 14, fontWeight: "600" },
});
