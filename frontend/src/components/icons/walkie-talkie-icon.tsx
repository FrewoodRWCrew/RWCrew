// A custom icon for Walkies' tile, since lucide-react has no walkie-talkie
// (its "Radio" icons are broadcast waves, not a handheld radio).
//
// Built with lucide-react's own createLucideIcon() helper so it's a drop-in
// LucideIcon — same 24x24 viewBox, 2px stroke, round caps/joins, no fill —
// and can be assigned to ModuleTheme.icon in module-theme.ts exactly like
// RollContainerIcon.

import { createLucideIcon } from "lucide-react";

// Drawn as a straight front view: an upright handset with a long antenna
// on the left, a short channel knob on the right and a speaker grille.
const WalkieTalkieIcon = createLucideIcon("walkie-talkie", [
  // The handset body, with rounded corners.
  ["rect", { x: "6", y: "8", width: "12", height: "14", rx: "2", key: "wt-body" }],
  // The long antenna, rising from the top-left of the body.
  ["path", { d: "M9 8V2", key: "wt-antenna" }],
  // The short channel knob on the top-right.
  ["path", { d: "M15 8V6", key: "wt-knob" }],
  // The speaker grille: three short horizontal bars.
  ["path", { d: "M10 12h4", key: "wt-grille-1" }],
  ["path", { d: "M10 15h4", key: "wt-grille-2" }],
  ["path", { d: "M10 18h4", key: "wt-grille-3" }],
]);

export default WalkieTalkieIcon;
