// An orange "TEST" corner label, shown only in the test variant of the app,
// so nobody mistakes it for the real production app (the web test site has
// the same kind of banner).

import { StyleSheet, Text, View } from "react-native";

import { useT } from "../i18n";
import { APP_VARIANT } from "../lib/config";

export function TestBanner() {
  const t = useT();
  if (APP_VARIANT !== "test") return null;
  return (
    <View style={styles.banner}>
      <Text style={styles.text}>{t("common.testBanner")}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: { alignSelf: "flex-end", backgroundColor: "#f59e0b", paddingHorizontal: 12, paddingVertical: 3, borderRadius: 4 },
  text: { color: "#000", fontWeight: "700", fontSize: 12 },
});
