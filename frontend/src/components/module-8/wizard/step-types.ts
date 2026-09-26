// The contract every Ploeg Wizard step component follows (see ./steps/index.ts
// for the registry that maps a step key to its component).

import type { AltsienSelectTeamState } from "@/lib/types";

/** A step's pending-changes saver: resolves true when saved (or nothing to
 *  save), false when saving failed and the wizard should stay on the step. */
export type StepSaver = () => Promise<boolean>;

export interface WizardStepProps {
  /** Everything chosen so far for this team and season. */
  state: AltsienSelectTeamState;
  teamId: number;
  seasonId: number;
  /** True once the season is closed (or the user may only look). */
  readOnly: boolean;
  /** Hand the wizard a fresh state after the step saved something. */
  onStateChange: (state: AltsienSelectTeamState) => void;
  /** Steps with a draft (unsaved choices) register a saver here, so the
   *  wizard's "Save" / "Complete step" buttons can store it first. */
  registerSave: (saver: StepSaver | null) => void;
}
