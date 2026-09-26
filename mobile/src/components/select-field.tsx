// A dropdown for a phone: a field showing the current choice that opens a
// full-screen list to pick from. Used for Ploeg, Status and Team kar.

import { useState } from "react";
import { FlatList, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useT } from "../i18n";
import { useColors } from "../lib/theme";

export type SelectOption<V> = { value: V; label: string };

type Props<V> = {
  label: string;
  value: V | null;
  options: SelectOption<V>[];
  onChange: (value: V | null) => void;
  // When set, a first entry with this text lets the user pick "nothing".
  noneLabel?: string;
  editable?: boolean;
};

export function SelectField<V extends string | number>({ label, value, options, onChange, noneLabel, editable = true }: Props<V>) {
  const t = useT();
  const colors = useColors();
  const [open, setOpen] = useState(false);

  const selected = options.find((option) => option.value === value);
  // The list shown in the picker, with the optional "none" entry on top.
  const entries: { value: V | null; label: string }[] = noneLabel ? [{ value: null, label: noneLabel }, ...options] : options;

  return (
    <View style={styles.field}>
      <Text style={[styles.label, { color: colors.muted }]}>{label}</Text>
      <Pressable
        onPress={() => editable && setOpen(true)}
        style={[
          styles.input,
          { borderColor: colors.border, backgroundColor: editable ? colors.inputBackground : colors.card },
        ]}
      >
        <Text style={[styles.value, { color: selected ? colors.text : colors.muted }]} numberOfLines={1}>
          {selected?.label ?? noneLabel ?? t("interventionRequests.requests.choose")}
        </Text>
        {editable && <Text style={{ color: colors.muted }}>▾</Text>}
      </Pressable>

      <Modal visible={open} animationType="slide" onRequestClose={() => setOpen(false)}>
        <SafeAreaView style={[styles.modal, { backgroundColor: colors.background }]}>
          <View style={[styles.modalHeader, { borderColor: colors.border }]}>
            <Text style={[styles.modalTitle, { color: colors.text }]}>{label}</Text>
            <Pressable onPress={() => setOpen(false)}>
              <Text style={[styles.close, { color: colors.brand }]}>{t("common.cancel")}</Text>
            </Pressable>
          </View>
          <FlatList
            data={entries}
            keyExtractor={(entry) => String(entry.value)}
            renderItem={({ item }) => (
              <Pressable
                onPress={() => {
                  onChange(item.value);
                  setOpen(false);
                }}
                style={[styles.row, { borderColor: colors.border }]}
              >
                <Text style={[styles.rowText, { color: colors.text }, item.value === value && { fontWeight: "700" }]}>
                  {item.label}
                </Text>
                {item.value === value && <Text style={{ color: colors.brand }}>✓</Text>}
              </Pressable>
            )}
          />
        </SafeAreaView>
      </Modal>
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
    paddingVertical: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  value: { fontSize: 16, flex: 1 },
  modal: { flex: 1 },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  modalTitle: { fontSize: 18, fontWeight: "700" },
  close: { fontSize: 16, fontWeight: "600" },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  rowText: { fontSize: 16, flex: 1 },
});
