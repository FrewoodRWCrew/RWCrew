// KarTracker's rolcontainer icon: the exact same drawing as the web app's
// frontend/src/components/icons/roll-container-icon.tsx (a straight front
// view of the wire-mesh container on small casters, reference picture
// Attachment/rolcontainer.jpg), in the same 24x24 grid with a 2px round
// stroke as the Feather/lucide icons used next to it.

import Svg, { Circle, Path, Rect } from "react-native-svg";

export function RollContainerIcon({ size, color }: { size: number; color: string }) {
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {/* The tall cage frame, with the rounded top corners of its tubes. */}
      <Rect x={6} y={2} width={12} height={15} rx={2} />
      {/* The wire mesh (3x3, the lower bar is the crossbar) and the base plate. */}
      <Path d="M10 2v15M14 2v15M6 7h12M6 12h12M4 17h16" />
      {/* Two of the four small casters, seen from the front. */}
      <Circle cx={7.5} cy={20.5} r={1.5} />
      <Circle cx={16.5} cy={20.5} r={1.5} />
    </Svg>
  );
}
