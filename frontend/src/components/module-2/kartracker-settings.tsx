"use client";

// KarTracker's "Instellingen" screen (screen key "kartracker.settings"): the
// karcode formula the Karcode Simulator computes lock codes with. Everyone
// with "view" can read and test it (the test runs the draft on the backend
// without saving, POST /settings/karcode/preview); only "edit" can save it,
// after a confirmation since every code shown from then on changes.

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { FlaskConical, Info, LockKeyhole, Save, Undo2 } from "lucide-react";
import { previewKarcodeFormula, updateKarcodeFormula } from "@/lib/api";
import type { KarTrackerSettings } from "@/lib/types";
import { formatDateTime } from "@/lib/date-time";
import { cn } from "@/lib/utils";
import { karcodeErrorMessage } from "@/components/module-2/karcode-common";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// Wait this long after the last change before testing the draft formula.
const PREVIEW_DEBOUNCE_MS = 400;
// Same limit as the backend.
const MAX_FORMULA_LENGTH = 500;

interface KarTrackerSettingsFormProps {
  initialSettings: KarTrackerSettings;
  canEdit: boolean;
}

export function KarTrackerSettingsForm({
  initialSettings,
  canEdit,
}: KarTrackerSettingsFormProps) {
  const t = useTranslations("karTracker.settings");
  const tKarcode = useTranslations("karTracker.karcode");
  const tCommon = useTranslations("common");

  // The saved settings, and the formula being edited.
  const [settings, setSettings] = useState(initialSettings);
  const [formula, setFormula] = useState(initialSettings.karcode_formula);
  const [isSaving, setIsSaving] = useState(false);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);

  // The test: a kar number and what the draft formula gives for it.
  const [testKar, setTestKar] = useState("36");
  const [testCode, setTestCode] = useState<string | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const previewIdRef = useRef(0);

  const isDirty = formula.trim() !== settings.karcode_formula;

  // Re-test the draft shortly after the formula or the kar number changes.
  useEffect(() => {
    const previewId = ++previewIdRef.current;
    const timer = window.setTimeout(async () => {
      if (!formula.trim() || !testKar.trim()) {
        setTestCode(null);
        setTestError(null);
        return;
      }
      try {
        const answer = await previewKarcodeFormula(formula, testKar);
        if (previewId !== previewIdRef.current) return;
        setTestCode(answer.code);
        setTestError(null);
      } catch (error) {
        if (previewId !== previewIdRef.current) return;
        setTestCode(null);
        setTestError(karcodeErrorMessage(tKarcode, error));
      }
    }, PREVIEW_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [formula, testKar, tKarcode]);

  async function handleSave() {
    setIsSaving(true);
    try {
      const saved = await updateKarcodeFormula(formula);
      setSettings(saved);
      setFormula(saved.karcode_formula);
      setIsConfirmOpen(false);
      toast.success(t("saved"));
    } catch (error) {
      toast.error(karcodeErrorMessage(tKarcode, error));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">
          {t("title")}
        </h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="grid max-w-5xl gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <LockKeyhole className="size-4 text-purple-600" />
              {t("formulaLabel")}
            </CardTitle>
            <CardDescription>
              {settings.karcode_updated_at
                ? t("lastChanged", {
                    name: settings.karcode_updated_by_name ?? "?",
                    date: formatDateTime(settings.karcode_updated_at),
                  })
                : t("neverChanged")}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            {/* The formula itself. */}
            <div className="flex flex-col gap-2">
              <Label htmlFor="karcode-formula">{t("formulaLabel")}</Label>
              <Textarea
                id="karcode-formula"
                value={formula}
                onChange={(event) => setFormula(event.target.value)}
                readOnly={!canEdit}
                maxLength={MAX_FORMULA_LENGTH}
                rows={3}
                spellCheck={false}
                className="font-mono text-base"
              />
              {!canEdit && (
                <p className="text-xs text-muted-foreground">{t("readOnly")}</p>
              )}
              {canEdit && isDirty && (
                <p className="text-xs text-amber-600 dark:text-amber-400">
                  {t("unsaved")}
                </p>
              )}
            </div>

            {/* Test the draft on one kar number. */}
            <div className="rounded-lg border bg-muted/40 p-4">
              <div className="mb-1 flex items-center gap-2 text-sm font-semibold">
                <FlaskConical className="size-4 text-purple-600" />
                {t("testTitle")}
              </div>
              <p className="mb-3 text-xs text-muted-foreground">
                {t("testHint")}
              </p>
              <div className="flex flex-wrap items-end gap-4">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="karcode-test-kar">{t("testKar")}</Label>
                  <Input
                    id="karcode-test-kar"
                    inputMode="numeric"
                    value={testKar}
                    onChange={(event) =>
                      setTestKar(
                        event.target.value.replace(/\D/g, "").slice(0, 10),
                      )
                    }
                    className="w-32"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <span className="text-sm font-medium">{t("testResult")}</span>
                  <span
                    className={cn(
                      "flex h-9 min-w-28 items-center justify-center rounded-md bg-zinc-900 px-3 font-mono text-xl font-bold tracking-[0.25em]",
                      testError ? "text-rose-300" : "text-yellow-300",
                    )}
                  >
                    {testError ? "Err" : (testCode ?? "—")}
                  </span>
                </div>
              </div>
              {testError && (
                <p className="mt-2 text-sm text-destructive">{testError}</p>
              )}
            </div>

            {/* Save / undo (only with "edit"). */}
            {canEdit && (
              <div className="flex flex-wrap gap-2">
                <AlertDialog
                  open={isConfirmOpen}
                  onOpenChange={setIsConfirmOpen}
                >
                  <AlertDialogTrigger
                    render={
                      <Button
                        disabled={
                          !isDirty ||
                          !formula.trim() ||
                          testError !== null ||
                          isSaving
                        }
                      >
                        <Save className="size-4" />
                        {t("save")}
                      </Button>
                    }
                  />
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>{t("confirmTitle")}</AlertDialogTitle>
                      <AlertDialogDescription>
                        {t("confirmDescription")}
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <code className="block rounded-md bg-muted px-3 py-2 font-mono text-sm break-all">
                      {formula.trim()}
                    </code>
                    <AlertDialogFooter>
                      <AlertDialogCancel>{tCommon("cancel")}</AlertDialogCancel>
                      <AlertDialogAction
                        disabled={isSaving}
                        onClick={handleSave}
                      >
                        {t("save")}
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
                <Button
                  variant="outline"
                  disabled={!isDirty || isSaving}
                  onClick={() => setFormula(settings.karcode_formula)}
                >
                  <Undo2 className="size-4" />
                  {t("reset")}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* How to write a formula. */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="size-4 text-purple-600" />
              {t("syntaxTitle")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex list-disc flex-col gap-2 pl-4 text-sm">
              <li>{t("syntaxVariable")}</li>
              <li>{t("syntaxOperators")}</li>
              <li>
                {t("syntaxFunctions", {
                  functions: settings.karcode_functions.join(", "),
                })}
              </li>
              <li>{t("syntaxSeparator")}</li>
              <li className="font-mono text-xs">{t("syntaxExample")}</li>
            </ul>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
