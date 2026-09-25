// The login screen (shown when nobody is logged in).

import { useState } from "react";
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { TestBanner } from "../components/test-banner";
import { Button, TextField, describeError } from "../components/ui";
import { useT } from "../i18n";
import { ApiError } from "../lib/api";
import { API_URL, APP_VARIANT, APP_VERSION } from "../lib/config";
import { useSession } from "../lib/session";
import { useColors } from "../lib/theme";

export default function LoginScreen() {
  const t = useT();
  const colors = useColors();
  const { signIn } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin() {
    setBusy(true);
    setError(null);
    try {
      // On success the session flips and Expo Router moves us to the landing page.
      await signIn(email.trim(), password);
    } catch (caught) {
      // 401 = wrong email/password; everything else (offline, old app...) gets its own message.
      if (caught instanceof ApiError && caught.status === 401) setError(t("login.invalidCredentials"));
      else setError(describeError(caught, t));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: colors.background }]}>
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          <TestBanner />
          <Text style={[styles.title, { color: colors.text }]}>{t("login.title")}</Text>

          <View style={styles.form}>
            <TextField
              label={t("login.emailLabel")}
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
            />
            <TextField
              label={t("login.passwordLabel")}
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoCapitalize="none"
              autoComplete="current-password"
            />
            {error !== null && <Text style={{ color: colors.danger }}>{error}</Text>}
            <Button
              title={busy ? t("login.submitting") : t("login.submit")}
              onPress={handleLogin}
              disabled={busy || email.trim() === "" || password === ""}
            />
          </View>

          <Text style={[styles.footer, { color: colors.muted }]}>
            v{APP_VERSION} · {APP_VARIANT} · {API_URL}
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  flex: { flex: 1 },
  content: { flexGrow: 1, padding: 24, justifyContent: "center", gap: 24 },
  title: { fontSize: 28, fontWeight: "700", textAlign: "center" },
  form: { gap: 14 },
  footer: { textAlign: "center", fontSize: 12 },
});
