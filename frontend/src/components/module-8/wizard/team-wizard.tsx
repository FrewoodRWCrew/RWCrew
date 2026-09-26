"use client";

// The Ploeg Wizard for one team: a clickable stepper across the top (done /
// current / to do), the current step's own component in the middle (see
// ./steps/index.ts), and Back / Save / "Complete step" buttons below.
// "Complete step" first stores the step's pending choices, then asks the
// backend to mark it done (which checks the step's rule, e.g. every chosen
// festival needs a delivery location) and moves on to the next step. When
// the season is closed the wizard is read-only and only shows the choices.

import { useCallback, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, FileText, Lock, RotateCcw, Save } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Link } from "@/i18n/navigation";
import { ApiError, getAltsienSelectWizard, setAltsienSelectStepComplete } from "@/lib/api";
import type { AltsienSelectStep, AltsienSelectTeamState, Season } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AltsienSeasonSelect, useAltsienSeasonId } from "@/components/module-8/altsien-season-select";
import { useKeyedLoad } from "@/components/module-8/use-keyed-load";
import { formatDate } from "@/components/module-8/wizard/format";
import type { StepSaver } from "@/components/module-8/wizard/step-types";
import { WizardStep } from "@/components/module-8/wizard/steps";
import { useStepText } from "@/components/module-8/wizard/use-step-text";

interface TeamWizardProps {
  teamId: number;
  seasons: Season[];
  canViewPloegfiche: boolean;
}

export function TeamWizard({ teamId, seasons, canViewPloegfiche }: TeamWizardProps) {
  const t = useTranslations("altsienSelect.wizard");
  const seasonId = useAltsienSeasonId(seasons);
  const wizard = useKeyedLoad<AltsienSelectTeamState>(seasonId === null ? null : `${seasonId}:${teamId}`, () =>
    getAltsienSelectWizard(teamId, seasonId as number),
  );

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Link
            href={seasonId !== null ? `/modules/module-8/ploeg-wizard?season=${seasonId}` : "/modules/module-8/ploeg-wizard"}
            className="mb-1 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            {t("backToTeams")}
          </Link>
          <h1 className="text-2xl font-bold tracking-tight underline">
            {wizard.data ? t("teamTitle", { team: wizard.data.team.name }) : t("title")}
          </h1>
        </div>
        <AltsienSeasonSelect seasons={seasons} seasonId={seasonId} />
      </div>

      {seasonId === null && <p className="text-sm text-muted-foreground">{t("noSeason")}</p>}
      {wizard.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {wizard.failed && <p className="text-sm text-destructive">{t("loadError")}</p>}
      {wizard.data && seasonId !== null && (
        <WizardBody
          // A fresh wizard (current step, drafts) per team + season.
          key={`${seasonId}:${teamId}`}
          state={wizard.data}
          teamId={teamId}
          seasonId={seasonId}
          canViewPloegfiche={canViewPloegfiche}
          onStateChange={wizard.setData}
        />
      )}
    </div>
  );
}

interface WizardBodyProps {
  state: AltsienSelectTeamState;
  teamId: number;
  seasonId: number;
  canViewPloegfiche: boolean;
  onStateChange: (state: AltsienSelectTeamState) => void;
}

function WizardBody({ state, teamId, seasonId, canViewPloegfiche, onStateChange }: WizardBodyProps) {
  const t = useTranslations("altsienSelect.wizard");
  const stepText = useStepText();
  const steps = state.steps;
  const doneByKey = new Map(state.progress.map((item) => [item.step_key, item]));
  const readOnly = !state.can_edit;

  // Start on the first step that isn't done yet (or the first one).
  const [currentKey, setCurrentKey] = useState<string>(
    () => (steps.find((step) => !doneByKey.has(step.key)) ?? steps[0])?.key ?? "",
  );
  const [isBusy, setIsBusy] = useState(false);
  // The current step's saver for pending choices (see step-types.ts).
  const saverRef = useRef<StepSaver | null>(null);
  const registerSave = useCallback((saver: StepSaver | null) => {
    saverRef.current = saver;
  }, []);

  const currentIndex = Math.max(
    0,
    steps.findIndex((step) => step.key === currentKey),
  );
  const currentStep: AltsienSelectStep | undefined = steps[currentIndex];
  const currentDone = currentStep ? doneByKey.get(currentStep.key) : undefined;
  const isLastStep = currentIndex === steps.length - 1;
  const allDone = steps.every((step) => doneByKey.has(step.key));

  // Store the step's pending choices; false when that failed.
  async function saveCurrent(): Promise<boolean> {
    return saverRef.current ? saverRef.current() : true;
  }

  // Leaving a step (via the stepper or Back) first stores its choices.
  async function goTo(stepKey: string) {
    if (stepKey === currentKey || isBusy) return;
    setIsBusy(true);
    try {
      if (readOnly || (await saveCurrent())) setCurrentKey(stepKey);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleSave() {
    setIsBusy(true);
    try {
      await saveCurrent();
    } finally {
      setIsBusy(false);
    }
  }

  async function handleComplete() {
    if (!currentStep) return;
    setIsBusy(true);
    try {
      if (!(await saveCurrent())) return;
      const updated = await setAltsienSelectStepComplete(teamId, seasonId, currentStep.key, true);
      onStateChange(updated);
      toast.success(t("stepCompleted", { step: stepText(currentStep).title }));
      if (!isLastStep) setCurrentKey(steps[currentIndex + 1].key);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("completeFailed"));
    } finally {
      setIsBusy(false);
    }
  }

  async function handleReopen() {
    if (!currentStep) return;
    setIsBusy(true);
    try {
      onStateChange(await setAltsienSelectStepComplete(teamId, seasonId, currentStep.key, false));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("completeFailed"));
    } finally {
      setIsBusy(false);
    }
  }

  if (!currentStep) {
    return <p className="text-sm text-muted-foreground">{t("noSteps")}</p>;
  }

  const ploegficheHref = `/modules/module-8/ploegfiche?season=${seasonId}&team=${teamId}`;

  return (
    <div className="flex flex-col gap-4">
      {readOnly && (
        <p className="flex items-center gap-2 rounded-md border bg-muted/50 px-3 py-2 text-sm">
          <Lock className="size-4 shrink-0" aria-hidden="true" />
          {t("readOnly")}
        </p>
      )}

      {allDone && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-green-600/40 bg-green-600/10 px-3 py-2 text-sm">
          <span className="flex items-center gap-2 font-medium">
            <Check className="size-4 text-green-600" aria-hidden="true" />
            {t("allDone")}
          </span>
          {canViewPloegfiche && (
            <Link href={ploegficheHref} className={buttonVariants({ variant: "outline", size: "sm" })}>
              <FileText className="size-4" />
              {t("openPloegfiche")}
            </Link>
          )}
        </div>
      )}

      {/* Stepper: one pill per step; done steps show a tick. */}
      <ol className="flex flex-wrap gap-2">
        {steps.map((step, index) => {
          const isDone = doneByKey.has(step.key);
          const isCurrent = step.key === currentStep.key;
          return (
            <li key={step.key}>
              <button
                type="button"
                onClick={() => goTo(step.key)}
                disabled={isBusy}
                aria-current={isCurrent ? "step" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm transition-colors",
                  isCurrent ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted",
                )}
              >
                <span
                  className={cn(
                    "flex size-5 items-center justify-center rounded-full text-xs font-semibold",
                    isDone
                      ? "bg-green-600 text-white"
                      : isCurrent
                        ? "bg-primary-foreground text-primary"
                        : "bg-muted text-muted-foreground",
                  )}
                >
                  {isDone ? <Check className="size-3.5" aria-hidden="true" /> : index + 1}
                </span>
                {stepText(step).title}
              </button>
            </li>
          );
        })}
      </ol>

      <Card>
        <CardHeader>
          <CardTitle>
            {t("stepOf", { current: currentIndex + 1, total: steps.length })} · {stepText(currentStep).title}
          </CardTitle>
          <CardDescription>{stepText(currentStep).description}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {/* Keyed by step, so each step starts with a fresh draft. */}
          <WizardStep
            key={currentStep.key}
            stepKey={currentStep.key}
            state={state}
            teamId={teamId}
            seasonId={seasonId}
            readOnly={readOnly}
            onStateChange={onStateChange}
            registerSave={registerSave}
          />

          {currentDone && (
            <p className="flex items-center gap-2 text-sm text-green-700 dark:text-green-400">
              <Check className="size-4" aria-hidden="true" />
              {t("stepDoneOn", {
                date: formatDate(currentDone.completed_at),
                name: currentDone.completed_by_name ?? "—",
              })}
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button
          variant="outline"
          disabled={isBusy || currentIndex === 0}
          onClick={() => goTo(steps[currentIndex - 1].key)}
        >
          <ArrowLeft className="size-4" />
          {t("previous")}
        </Button>

        {!readOnly && (
          <div className="flex flex-wrap gap-2">
            {currentDone && (
              <Button variant="ghost" disabled={isBusy} onClick={handleReopen}>
                <RotateCcw className="size-4" />
                {t("reopen")}
              </Button>
            )}
            <Button variant="outline" disabled={isBusy} onClick={handleSave}>
              <Save className="size-4" />
              {t("save")}
            </Button>
            <Button disabled={isBusy} onClick={handleComplete}>
              {isLastStep ? t("completeLast") : t("completeNext")}
              {isLastStep ? <Check className="size-4" /> : <ArrowRight className="size-4" />}
            </Button>
          </div>
        )}
        {readOnly && !isLastStep && (
          <Button variant="outline" onClick={() => goTo(steps[currentIndex + 1].key)}>
            {t("next")}
            <ArrowRight className="size-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
