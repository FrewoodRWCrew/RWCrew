// KarScan (KarTracker > Acties): a full-screen QR scanner. The QR code on a kar
// holds its kar number; once scanned, the kar is looked up and its movement
// form opens. An unknown kar shows a message and scanning simply resumes.
// Scanning is the only way in — there is no typed kar number on purpose.

import { CameraView, useCameraPermissions, type BarcodeScanningResult } from "expo-camera";
import { useFocusEffect, useRouter } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { ActivityIndicator, Alert, Linking, StyleSheet, Text, View } from "react-native";

import { useModule2Permissions } from "../../../components/module-2/module-2-context";
import { Button, Centered, Loading, describeError } from "../../../components/ui";
import { useT } from "../../../i18n";
import { ApiError } from "../../../lib/api";
import { module2Api } from "../../../lib/module-api";
import { getModuleTheme } from "../../../lib/module-theme";
import { useColors } from "../../../lib/theme";

export default function KarScanScreen() {
  const t = useT();
  const router = useRouter();
  const colors = useColors();
  const theme = getModuleTheme("module-2");
  const permissions = useModule2Permissions();
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();

  // The camera only runs while this screen is on top (saves battery, and
  // stops it scanning in the background while the form is open).
  const [isFocused, setIsFocused] = useState(true);
  // The kar number being looked up right now, shown over the camera.
  const [lookingUp, setLookingUp] = useState<string | null>(null);
  // The camera fires many times per second for the same code: this lock
  // makes sure one scan is handled at a time.
  const scanLockRef = useRef(false);

  // Coming back from the form (or an alert) unlocks the scanner again.
  useFocusEffect(
    useCallback(() => {
      setIsFocused(true);
      scanLockRef.current = false;
      setLookingUp(null);
      return () => setIsFocused(false);
    }, []),
  );

  // Releases the lock so the next QR code can be scanned.
  function resumeScanning() {
    setLookingUp(null);
    scanLockRef.current = false;
  }

  async function handleScanned({ data }: BarcodeScanningResult) {
    if (scanLockRef.current) return;
    const karNummer = data.trim();
    if (!karNummer) return;
    scanLockRef.current = true;
    setLookingUp(karNummer);

    try {
      // Check the kar exists before opening its form.
      const scan = await module2Api.karByNummer(karNummer);
      router.push({ pathname: "/module-2/kar/[nummer]", params: { nummer: scan.kar.kar_nummer } });
    } catch (caught) {
      const message =
        caught instanceof ApiError && caught.status === 404
          ? t("karScan.karNotFound", { kar: karNummer })
          : describeError(caught, t);
      // Scanning resumes once the message is closed.
      Alert.alert(t("karScan.moduleTitle"), message, [{ text: "OK", onPress: resumeScanning }], {
        onDismiss: resumeScanning,
      });
    }
  }

  // Without "view" on Manuele kar beweging, a scan could never be looked up.
  if (!permissions.can_view_actions) {
    return (
      <Centered>
        <Text style={[styles.message, { color: colors.text }]}>{t("karScan.noViewRights")}</Text>
      </Centered>
    );
  }

  // The camera permission is still being read.
  if (!cameraPermission) return <Loading />;

  // Not allowed (yet): ask, or send the user to the settings once the phone
  // won't ask again.
  if (!cameraPermission.granted) {
    return (
      <Centered>
        <Text style={[styles.message, { color: colors.text }]}>{t("karScan.cameraNeeded")}</Text>
        {cameraPermission.canAskAgain ? (
          <Button title={t("karScan.allowCamera")} color={theme.tileColor} onPress={requestCameraPermission} />
        ) : (
          <Button title={t("karScan.openSettings")} color={theme.tileColor} onPress={() => void Linking.openSettings()} />
        )}
      </Centered>
    );
  }

  return (
    <View style={styles.container}>
      {isFocused && (
        <CameraView
          style={StyleSheet.absoluteFill}
          facing="back"
          barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
          onBarcodeScanned={lookingUp === null ? handleScanned : undefined}
        />
      )}

      {/* A square aiming frame in the middle of the camera image. */}
      <View pointerEvents="none" style={styles.frameWrapper}>
        <View style={[styles.frame, { borderColor: theme.tileColor }]} />
      </View>

      {/* What to do, or which kar is being looked up. */}
      <View style={styles.banner}>
        {lookingUp !== null ? (
          <View style={styles.lookingUp}>
            <ActivityIndicator color="#ffffff" />
            <Text style={styles.bannerText}>{t("karScan.looking", { kar: lookingUp })}</Text>
          </View>
        ) : (
          <>
            <Text style={[styles.bannerText, styles.bannerTitle]}>{t("karScan.scanTitle")}</Text>
            <Text style={styles.bannerText}>{t("karScan.scanHint")}</Text>
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000000" },
  message: { fontSize: 16, textAlign: "center" },
  frameWrapper: { position: "absolute", top: 0, right: 0, bottom: 0, left: 0, alignItems: "center", justifyContent: "center" },
  frame: { width: 240, height: 240, borderWidth: 4, borderRadius: 16 },
  banner: {
    position: "absolute",
    left: 16,
    right: 16,
    bottom: 32,
    borderRadius: 12,
    padding: 16,
    gap: 4,
    backgroundColor: "rgba(0, 0, 0, 0.65)",
  },
  bannerTitle: { fontSize: 17, fontWeight: "700" },
  bannerText: { color: "#ffffff", fontSize: 15, textAlign: "center" },
  lookingUp: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
});
