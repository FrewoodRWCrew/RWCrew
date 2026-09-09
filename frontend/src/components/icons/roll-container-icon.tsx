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

const RollContainerIcon = createLucideIcon("roll-container", [
  // The cage body — the container's rectangular wire-mesh frame.
  ["rect", { x: "4", y: "5", width: "15", height: "12", rx: "1", key: "rc-body" }],
  // The two vertical mesh dividers inside the frame.
  ["path", { d: "M9.5 5v12", key: "rc-mesh-1" }],
  ["path", { d: "M14.5 5v12", key: "rc-mesh-2" }],
  // The horizontal shelf partway up the cage.
  ["path", { d: "M4 11h15", key: "rc-shelf" }],
  // The raised push handle spanning the top of the frame.
  ["path", { d: "M7 5V3h10v2", key: "rc-handle" }],
  // The four swivel casters at the base — drawn as two, seen from the front.
  ["path", { d: "M8 17v2", key: "rc-leg-1" }],
  ["path", { d: "M15 17v2", key: "rc-leg-2" }],
  ["circle", { cx: "8", cy: "20", r: "1.5", key: "rc-wheel-1" }],
  ["circle", { cx: "15", cy: "20", r: "1.5", key: "rc-wheel-2" }],
]);

export default RollContainerIcon;
