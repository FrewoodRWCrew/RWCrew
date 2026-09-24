// The small building blocks every screen uses: centered states (loading /
// error), buttons, text fields and cards. Colours follow light/dark mode.

import type { ReactNode } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type KeyboardTypeOptions,
  type StyleProp,
  type ViewStyle,
} from "react-native";

import { useT } from "../i18n";
import { ApiError } from "../lib/api";
import { useColors } from "../lib/theme";

// Fills the space and centers its content (loading spinners, messages).
export function Centered({ children }: { children: ReactNode }) {
  return <View style={styles.centered}>{children}</View>;
}

export function Loading() {
  const t = useT();
  const colors = useColors();
  return (
    <Centered>
      <ActivityIndicator />
      <Text style={[styles.muted, { color: colors.muted }]}>{t("common.loading")}</Text>
    </Centered>
  );
}

// Turn any error into a message a user can act on.
export function describeError(error: unknown, t: ReturnType<typeof useT>): string {
  if (error instanceof ApiError) {
    // 426: this app build is older than the backend's minimum version.
    if (error.status === 426) return t("errors.updateRequired");
    if (error.status === 403) return t("errors.forbidden");
    return error.message || t("errors.generic");
  }
  // fetch() itself failed (no connection, server down): a TypeError.
  if (error instanceof TypeError) return t("errors.offline");
  return t("errors.generic");
}

// A full-screen error with a "try again" button.
export function ErrorView({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  const t = useT();
  const colors = useColors();
  const text = describeError(error, t);
  return (
    <Centered>
      <Text style={[styles.errorText, { color: colors.danger }]}>{text}</Text>
      {onRetry && <Button title={t("common.retry")} onPress={onRetry} />}
    </Centered>
  );
}

type ButtonProps = {
  title: string;
  onPress: () => void;
  disabled?: boolean;
  // Fill colour; defaults to the brand green.
  color?: string;
  textColor?: string;
  style?: StyleProp<ViewStyle>;
};

export function Button({ title, onPress, disabled, color, textColor, style }: ButtonProps) {
  const colors = useColors();
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={[styles.button, { backgroundColor: color ?? colors.brand }, disabled && styles.disabled, style]}
    >
      <Text style={[styles.buttonText, { color: textColor ?? colors.onBrand }]}>{title}</Text>
    </Pressable>
  );
}

type TextFieldProps = {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  editable?: boolean;
  multiline?: boolean;
  keyboardType?: KeyboardTypeOptions;
  secureTextEntry?: boolean;
  autoCapitalize?: "none" | "sentences";
  placeholder?: string;
  error?: string | null;
};

export function TextField(props: TextFieldProps) {
  const colors = useColors();
  const { label, value, onChangeText, editable = true, multiline, error } = props;
  return (
    <View style={styles.field}>
      <Text style={[styles.label, { color: colors.muted }]}>{label}</Text>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        editable={editable}
        multiline={multiline}
        keyboardType={props.keyboardType}
        secureTextEntry={props.secureTextEntry}
        autoCapitalize={props.autoCapitalize}
        autoCorrect={false}
        placeholder={props.placeholder}
        placeholderTextColor={colors.muted}
        style={[
          styles.input,
          multiline && styles.multiline,
          {
            color: colors.text,
            borderColor: error ? colors.danger : colors.border,
            backgroundColor: editable ? colors.inputBackground : colors.card,
          },
        ]}
      />
      {error ? <Text style={[styles.fieldError, { color: colors.danger }]}>{error}</Text> : null}
    </View>
  );
}

// A rounded panel with a soft background.
export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  const colors = useColors();
  return <View style={[styles.card, { backgroundColor: colors.card }, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  centered: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, gap: 12 },
  muted: { fontSize: 14 },
  errorText: { fontSize: 16, textAlign: "center" },
  button: { borderRadius: 8, paddingVertical: 14, paddingHorizontal: 20, alignItems: "center" },
  buttonText: { fontSize: 16, fontWeight: "600" },
  disabled: { opacity: 0.5 },
  field: { gap: 4 },
  label: { fontSize: 13, fontWeight: "600" },
  input: { borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, fontSize: 16 },
  multiline: { minHeight: 96, textAlignVertical: "top" },
  fieldError: { fontSize: 13 },
  card: { borderRadius: 12, padding: 16 },
});
