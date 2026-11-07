"use client";

// The Ploeg Wizard for one team: a clickable stepper across the top (done /
// current / to do), the current step's own component in the middle (see
// ./steps/index.ts), and Back / Save / "Complete step" buttons below.
// "Complete step" first stores the step's pending choices, then asks the
// backend to mark it done (which checks the step's rule, e.g. every chosen
// festival needs a delivery location) and moves on to the next step. When
// the season is closed the wizard is read-only and only shows the choices.
// Steps that offer it get a "copy from last season" panel above them (see
// copy-previous-season.tsx).

import { useCallback, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Check, ChevronRight, FileText, Lock, RotateCcw, Save } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { Link } from "@/i18n/navigation";
import {
  ApiError,
  copyAltsienSelectPreviousSeason,
  getAltsienSelectWizard,
  setAltsienSelectStepComplete,
} from "@/lib/api";
import type { AltsienSelectStep, AltsienSelectTeamState, Season } from "@/lib/types";
import { getModuleTheme } from "@/lib/module-theme";
import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AltsienSeasonSelect, useAltsienSeasonId } from "@/components/module-8/altsien-season-select";
import { useKeyedLoad } from "@/components/module-8/use-keyed-load";
import { CopyPreviousSeason } from "@/components/module-8/wizard/copy-previous-season";
import {
  PloegficheMailButton,
  PloegficheMailDialog,
  usePloegficheMail,
} from "@/components/module-8/wizard/ploegfiche-mail";
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
  // Bumped after a copy from last season, so the step remounts and its
  // draft starts from the copied values.
  const [copyVersion, setCopyVersion] = useState(0);
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
  // How many steps are done, for the progress bar above the stepper.
  const doneCount = steps.filter((step) => doneByKey.has(step.key)).length;
  // The module's soft accent (fuchsia) tint, used for the step card's header.
  const { badgeClassName } = getModuleTheme("module-8");
  // The Ploegfiche PDF by mail: asked once the last open step is completed.
  const ploegficheMail = usePloegficheMail(teamId, seasonId);
  const [askMail, setAskMail] = useState(false);

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
      // This completion finished the whole wizard: offer the PDF by mail.
      const doneNow = new Set(updated.progress.map((item) => item.step_key));
      if (!allDone && updated.steps.every((step) => doneNow.has(step.key))) setAskMail(true);
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

  // Copy last season's chosen lines into this step. Pending choices are
  // stored first, so the copy never overwrites (or gets overwritten by) a draft.
  async function handleCopyPrevious(lineKeys: string[]): Promise<boolean> {
    if (!currentStep) return false;
    setIsBusy(true);
    try {
      if (!(await saveCurrent())) return false;
      onStateChange(await copyAltsienSelectPreviousSeason(teamId, seasonId, currentStep.key, lineKeys));
      setCopyVersion((version) => version + 1);
      toast.success(t("previousSeason.copied"));
      return true;
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("previousSeason.copyFailed"));
      return false;
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
          <div className="flex flex-wrap gap-2">
            <PloegficheMailButton isSending={ploegficheMail.isSending} onSend={ploegficheMail.send} />
            {canViewPloegfiche && (
              <Link href={ploegficheHref} className={buttonVariants({ variant: "outline", size: "sm" })}>
                <FileText className="size-4" />
                {t("openPloegfiche")}
              </Link>
            )}
          </div>
        </div>
      )}
      <PloegficheMailDialog
        open={askMail}
        onOpenChange={setAskMail}
        isSending={ploegficheMail.isSending}
        onSend={ploegficheMail.send}
      />

      {/* Progress: "x / y steps done" with a thin bar in the module's accent. */}
      <div className="flex flex-col gap-1.5">
        <p className="text-sm font-medium">{t("progress", { done: doneCount, total: steps.length })}</p>
        <div
          className="h-2 w-full overflow-hidden rounded-full bg-muted"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={steps.length}
          aria-valuenow={doneCount}
        >
          <div
            className={cn("h-full rounded-full transition-all", allDone ? "bg-green-600" : "bg-primary")}
            style={{ width: `${steps.length > 0 ? (doneCount / steps.length) * 100 : 0}%` }}
          />
        </div>
      </div>

      {/* Stepper: one pill per step. Current = filled accent with a ring,
          done = soft green with a tick, still to do = dashed accent outline,
          so it's clear at a glance where work is left. A chevron links the
          pills on wider screens. */}
      <ol className="flex flex-wrap items-center gap-2">
        {steps.map((step, index) => {
          const isDone = doneByKey.has(step.key);
          const isCurrent = step.key === currentStep.key;
          return (
            <li key={step.key} className="flex items-center gap-2">
              {index > 0 && (
                <ChevronRight className="hidden size-4 shrink-0 text-muted-foreground/60 md:block" aria-hidden="true" />
              )}
              <button
                type="button"
                onClick={() => goTo(step.key)}
                disabled={isBusy}
                aria-current={isCurrent ? "step" : undefined}
                className={cn(
                  "flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-medium transition-all",
                  isCurrent
                    ? "scale-105 border-primary bg-primary text-primary-foreground shadow-md ring-2 ring-primary/30 ring-offset-2 ring-offset-background"
                    : isDone
                      ? "border-green-600/40 bg-green-600/10 text-green-800 hover:bg-green-600/20 dark:text-green-300"
                      : "border-dashed border-primary/60 bg-background text-foreground hover:bg-primary/10",
                )}
              >
                <span
                  className={cn(
                    "flex size-5 items-center justify-center rounded-full text-xs font-semibold",
                    isCurrent
                      ? "bg-primary-foreground text-primary"
                      : isDone
                        ? "bg-green-600 text-white"
                        : "bg-primary/15 text-primary",
                  )}
                >
                  {isDone && !isCurrent ? <Check className="size-3.5" aria-hidden="true" /> : index + 1}
                </span>
                {stepText(step).title}
              </button>
            </li>
          );
        })}
      </ol>

      {/* The step itself: accent line on top, tinted header with a big step
          number, so the working area clearly stands out from the page. */}
      <Card className="gap-0 border-t-4 border-t-primary py-0 shadow-md">
        <CardHeader className={cn("gap-2 border-b py-4", badgeClassName)}>
          <div className="flex flex-wrap items-center gap-4">
            <span
              className="flex size-11 shrink-0 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground shadow-sm"
              aria-hidden="true"
            >
              {currentDone ? <Check className="size-6" /> : currentIndex + 1}
            </span>
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <span className="text-xs font-semibold tracking-wide uppercase opacity-80">
                {t("stepOf", { current: currentIndex + 1, total: steps.length })}
              </span>
              <CardTitle className="text-xl font-bold text-foreground">{stepText(currentStep).title}</CardTitle>
            </div>
            {/* "Done on … by …" as a green pill, next to the title. */}
            {currentDone && (
              <span className="flex items-center gap-1.5 rounded-full border border-green-600/40 bg-green-600/15 px-3 py-1 text-xs font-medium text-green-800 dark:text-green-300">
                <Check className="size-3.5" aria-hidden="true" />
                {t("stepDoneOn", {
                  date: formatDate(currentDone.completed_at),
                  name: currentDone.completed_by_name ?? "—",
                })}
              </span>
            )}
          </div>
          {/* The step's question, in normal text colour so it's read first. */}
          <CardDescription className="text-base text-foreground sm:pl-15">
            {stepText(currentStep).description}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4 py-5">
          {currentStep.copy_from_previous && !readOnly && (
            <CopyPreviousSeason
              key={currentStep.key}
              teamId={teamId}
              seasonId={seasonId}
              stepKey={currentStep.key}
              disabled={isBusy}
              onCopy={handleCopyPrevious}
            />
          )}

          {/* Keyed by step (and copy), so each step starts with a fresh draft. */}
          <WizardStep
            key={`${currentStep.key}:${copyVersion}`}
            stepKey={currentStep.key}
            state={state}
            teamId={teamId}
            seasonId={seasonId}
            readOnly={readOnly}
            onStateChange={onStateChange}
            registerSave={registerSave}
          />
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
