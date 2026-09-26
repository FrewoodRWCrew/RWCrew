// A custom icon for Altsien Select's tile, echoing the Altsien logo
// (public/altsien-logo.png): a bold "A" whose crossbar is one long swoosh
// that sweeps out past both legs. No lucide-react icon comes close, so it is
// drawn here with lucide's own createLucideIcon() helper — same 24x24
// viewBox, 2px stroke, round caps/joins, no fill as every other tile icon —
// and assigned to ModuleTheme.icon in module-theme.ts like RollContainerIcon.

import { createLucideIcon } from "lucide-react";

const AltsienIcon = createLucideIcon("altsien", [
  // The two legs of the "A", meeting in a point at the top.
  ["path", { d: "M5 21 12 3l6 18", key: "altsien-legs" }],
  // The logo's signature crossbar: a curved swoosh reaching past both legs.
  ["path", { d: "M2 17.5c6-3.5 13-4.5 20-2.5", key: "altsien-swoosh" }],
]);

export default AltsienIcon;
