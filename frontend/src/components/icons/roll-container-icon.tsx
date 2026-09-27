// A custom icon for KarTracker's tile, since no existing lucide-react icon
// resembles a wire-mesh roll container on casters (see
// Attachment/rolcontainer.jpg — the reference picture for this module,
// the same way Attachment/Box.png guided module-3's "Box" icon choice).
//
// Built with lucide-react's own createLucideIcon() helper so it's a drop-in
// LucideIcon — same 24x24 viewBox, 2px stroke, round caps/joins, no fill —
// and can be assigned to ModuleTheme.icon in module-theme.ts exactly like
// Box/Nfc/Database.

import { createLucideIcon } from "lucide-react";

// Drawn as a straight front view: tall and narrow like the real container
// (about twice as high as wide), no push handle, small casters. The phone
// app draws the exact same shapes (mobile/src/components/roll-container-icon.tsx).
const RollContainerIcon = createLucideIcon("roll-container", [
  // The tall cage frame, with the rounded top corners of its tubes.
  ["rect", { x: "6", y: "2", width: "12", height: "15", rx: "2", key: "rc-body" }],
  // The wire mesh: two vertical and two horizontal bars (the lower one is
  // the crossbar halfway up), giving a 3x3 grid.
  ["path", { d: "M10 2v15", key: "rc-mesh-1" }],
  ["path", { d: "M14 2v15", key: "rc-mesh-2" }],
  ["path", { d: "M6 7h12", key: "rc-mesh-3" }],
  ["path", { d: "M6 12h12", key: "rc-crossbar" }],
  // The low base plate, a little wider than the cage.
  ["path", { d: "M4 17h16", key: "rc-base" }],
  // The four small swivel casters — drawn as two, seen from the front.
  ["circle", { cx: "7.5", cy: "20.5", r: "1.5", key: "rc-wheel-1" }],
  ["circle", { cx: "16.5", cy: "20.5", r: "1.5", key: "rc-wheel-2" }],
]);

export default RollContainerIcon;
