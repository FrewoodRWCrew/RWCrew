// Everything a logged-in user can reach: the landing page and the modules.
// Each module draws its own headers, so this stack has none.

import { Stack } from "expo-router";

export default function AppLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
