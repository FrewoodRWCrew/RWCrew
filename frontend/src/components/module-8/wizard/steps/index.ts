// The Ploeg Wizard's step registry: which component renders which step key.
// The steps themselves (order, placeholder flag, completion rules) are
// defined once in the backend (app/modules/module_8/steps.py) and arrive
// with the team's state. To add a step: add it there, add its component
// here, and give it a title/description under "altsienSelect.steps.<key>"
// in messages/*.json. A key without a component here falls back to the
// generic PlaceholderStep, so a new backend step never breaks the wizard.

import { createElement, type ComponentType, type ReactElement } from "react";
import { AfleverlocatieStep } from "@/components/module-8/wizard/steps/afleverlocatie-step";
import { FestivalStep } from "@/components/module-8/wizard/steps/festival-step";
import { PlaceholderStep } from "@/components/module-8/wizard/steps/placeholder-step";
import { SpecialRequestsStep } from "@/components/module-8/wizard/steps/special-requests-step";
import type { WizardStepProps } from "@/components/module-8/wizard/step-types";

const STEP_COMPONENTS: Record<string, ComponentType<WizardStepProps>> = {
  festivals: FestivalStep,
  afleverlocaties: AfleverlocatieStep,
  // products: placeholder until the products module exists.
  special_requests: SpecialRequestsStep,
  // walkies: placeholder until the walkie-talkie module exists.
};

/** Renders the component registered for a step (or the placeholder). */
export function WizardStep({ stepKey, ...props }: WizardStepProps & { stepKey: string }): ReactElement {
  return createElement(STEP_COMPONENTS[stepKey] ?? PlaceholderStep, props);
}
