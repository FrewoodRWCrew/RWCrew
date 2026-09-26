// The landing page shown right after login — the phone version of the web
// "Overzicht Modules" page: a grid of coloured tiles, one per module this
// user may open (for now only Interventie Aanvragen).

import { useRouter } from "expo-router";
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View, useWindowDimensions } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ModuleTile } from "../../components/module-tile";
import { TestBanner } from "../../components/test-banner";
import { ErrorView, Loading } from "../../components/ui";
import { useT } from "../../i18n";
import { API_URL, APP_VARIANT, APP_VERSION } from "../../lib/config";
import { listModules } from "../../lib/module-api";
import { isKnownModule } from "../../lib/module-theme";
import { useSession } from "../../lib/session";
import { useColors } from "../../lib/theme";
import { useAsync } from "../../lib/use-async";

// Space between tiles and around the grid.
const GAP = 16;
const COLUMNS = 2;

export default function LandingScreen() {
  const t = useT();
  const colors = useColors();
  const router = useRouter();
  const { user, signOut } = useSession();
  const { width } = useWindowDimensions();
  const { data, error, loading, refreshing, reload } = useAsync(listModules);

  // Each tile takes an equal share of the row.
  const tileWidth = (width - GAP * (COLUMNS + 1)) / COLUMNS;

  if (loading) return <Loading />;
  if (error) return <ErrorView error={error} onRetry={reload} />;

  // Only modules this app version knows how to open, in tile order.
  const modules = (data ?? []).filter((module) => isKnownModule(module.key)).sort((a, b) => a.sort_order - b.sort_order);

  return (
    <SafeAreaView style={[styles.screen, { backgroundColor: colors.background }]}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={reload} />}
      >
        <TestBanner />

        {/* Who is logged in + log out (the web's user menu). */}
        <View style={styles.userRow}>
          <Text style={[styles.hello, { color: colors.muted }]} numberOfLines={1}>
            {t("landing.hello", { name: user?.display_name ?? "" })}
          </Text>
          <Pressable onPress={signOut} accessibilityRole="button">
            <Text style={[styles.logout, { color: colors.brand }]}>{t("common.logout")}</Text>
          </Pressable>
        </View>

        <View>
          <Text style={[styles.title, { color: colors.text }]}>{t("landing.title")}</Text>
          <Text style={{ color: colors.muted }}>{t("landing.subtitle")}</Text>
        </View>

        {modules.length === 0 ? (
          <Text style={[styles.noAccess, { color: colors.muted, borderColor: colors.border }]}>{t("landing.noAccess")}</Text>
        ) : (
          <View style={styles.grid}>
            {modules.map((module) => (
              <ModuleTile
                key={module.key}
                module={module}
                width={tileWidth}
                onPress={() => router.push(`/${module.key}`)}
              />
            ))}
          </View>
        )}

        <Text style={[styles.footer, { color: colors.muted }]}>
          v{APP_VERSION} · {APP_VARIANT} · {API_URL}
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1 },
  content: { padding: GAP, gap: GAP, flexGrow: 1 },
  userRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 12 },
  hello: { flex: 1, fontSize: 14 },
  logout: { fontSize: 15, fontWeight: "600" },
  title: { fontSize: 26, fontWeight: "700" },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: GAP },
  noAccess: { borderWidth: 1, borderStyle: "dashed", borderRadius: 8, padding: 16 },
  footer: { textAlign: "center", fontSize: 12, marginTop: "auto", paddingTop: 24 },
});
