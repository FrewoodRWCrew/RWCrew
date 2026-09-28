"use client";

// Ploeg Wizard step 3: the team's responsible people ("Ploegverantwoordelijken")
// for this season, with their contact details. They are not RWCrew users.
// Each person is saved straight away (no draft), into MasterData's own
// table — the same rows MasterData's "Ploegverantwoordelijken" screen shows.
// The step can only be completed once at least one person is listed.

import { useState } from "react";
import { Mail, Pencil, Phone, Plus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ApiError,
  createAltsienSelectResponsible,
  deleteAltsienSelectResponsible,
  updateAltsienSelectResponsible,
} from "@/lib/api";
import type { AltsienSelectResponsibleInput, TeamResponsible } from "@/lib/types";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { WizardStepProps } from "@/components/module-8/wizard/step-types";

const EMPTY_FORM: AltsienSelectResponsibleInput = { name: "", email: "", phone: "", comments: "" };

// Same order as the backend returns them: by name.
function sortByName(people: TeamResponsible[]) {
  return [...people].sort((a, b) => a.name.localeCompare(b.name) || a.id - b.id);
}

export function PloegverantwoordelijkenStep({ state, teamId, seasonId, readOnly, onStateChange }: WizardStepProps) {
  const t = useTranslations("altsienSelect.steps.ploegverantwoordelijken");

  // Keep the wizard's state in sync after each change.
  function replaceResponsibles(responsibles: TeamResponsible[]) {
    onStateChange({ ...state, responsibles: sortByName(responsibles) });
  }

  return (
    <div className="flex flex-col gap-3">
      {!readOnly && (
        <div>
          <ResponsibleFormDialog
            trigger={
              <Button variant="outline">
                <Plus className="size-4" />
                {t("add")}
              </Button>
            }
            onSubmit={async (input) => {
              const created = await createAltsienSelectResponsible(teamId, seasonId, input);
              replaceResponsibles([...state.responsibles, created]);
            }}
          />
        </div>
      )}

      {state.responsibles.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {state.responsibles.map((person) => (
            <li key={person.id} className="flex flex-col gap-1 rounded-md border p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="font-medium">{person.name}</p>
                {!readOnly && (
                  <div className="flex shrink-0 items-center gap-1">
                    <ResponsibleFormDialog
                      person={person}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label={t("edit")} title={t("edit")}>
                          <Pencil className="size-4" />
                        </Button>
                      }
                      onSubmit={async (input) => {
                        const updated = await updateAltsienSelectResponsible(teamId, person.id, input);
                        replaceResponsibles(
                          state.responsibles.map((item) => (item.id === updated.id ? updated : item)),
                        );
                      }}
                    />
                    <DeleteResponsibleDialog
                      name={person.name}
                      onConfirm={async () => {
                        await deleteAltsienSelectResponsible(teamId, person.id);
                        replaceResponsibles(state.responsibles.filter((item) => item.id !== person.id));
                      }}
                    />
                  </div>
                )}
              </div>
              {/* Contact details, clickable to mail or call. */}
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                <a href={`mailto:${person.email}`} className="flex items-center gap-1 hover:underline">
                  <Mail className="size-3.5" />
                  {person.email}
                </a>
                <a href={`tel:${person.phone}`} className="flex items-center gap-1 hover:underline">
                  <Phone className="size-3.5" />
                  {person.phone}
                </a>
              </div>
              {person.comments && <p className="text-sm whitespace-pre-wrap">{person.comments}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface ResponsibleFormDialogProps {
  person?: TeamResponsible;
  trigger: React.ReactElement;
  onSubmit: (input: AltsienSelectResponsibleInput) => Promise<void>;
}

/** Add or change one responsible person. */
function ResponsibleFormDialog({ person, trigger, onSubmit }: ResponsibleFormDialogProps) {
  const t = useTranslations("altsienSelect.steps.ploegverantwoordelijken");
  const [isOpen, setIsOpen] = useState(false);
  const [form, setForm] = useState<AltsienSelectResponsibleInput>(EMPTY_FORM);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    // Start from the person's current details each time.
    if (open) {
      setForm(
        person
          ? { name: person.name, email: person.email, phone: person.phone, comments: person.comments ?? "" }
          : EMPTY_FORM,
      );
    }
  }

  function updateField<K extends keyof AltsienSelectResponsibleInput>(
    field: K,
    value: AltsienSelectResponsibleInput[K],
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  // Everything except the comments is required.
  const isComplete = form.name.trim() !== "" && form.email.trim() !== "" && form.phone.trim() !== "";

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      await onSubmit({ ...form, email: form.email.trim(), comments: form.comments?.trim() || null });
      toast.success(person ? t("updated") : t("created"));
      setIsOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveFailed"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger render={trigger} />
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{person ? t("editTitle") : t("addTitle")}</DialogTitle>
          <DialogDescription>{t("dialogDescription")}</DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="altsien-responsible-name">{t("nameLabel")}</Label>
            <Input
              id="altsien-responsible-name"
              value={form.name}
              onChange={(event) => updateField("name", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="altsien-responsible-email">{t("emailLabel")}</Label>
            <Input
              id="altsien-responsible-email"
              type="email"
              value={form.email}
              onChange={(event) => updateField("email", event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="altsien-responsible-phone">{t("phoneLabel")}</Label>
            <Input
              id="altsien-responsible-phone"
              type="tel"
              value={form.phone}
              onChange={(event) => updateField("phone", event.target.value)}
            />
          </div>
          <div className="col-span-2 flex flex-col gap-2">
            <Label htmlFor="altsien-responsible-comments">{t("commentsLabel")}</Label>
            <Textarea
              id="altsien-responsible-comments"
              maxLength={5000}
              value={form.comments ?? ""}
              onChange={(event) => updateField("comments", event.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !isComplete}>
            {person ? t("save") : t("add")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Confirm removing a responsible person. */
function DeleteResponsibleDialog({ name, onConfirm }: { name: string; onConfirm: () => Promise<void> }) {
  const t = useTranslations("altsienSelect.steps.ploegverantwoordelijken");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirm() {
    setIsDeleting(true);
    try {
      await onConfirm();
      toast.success(t("deleted"));
      setIsOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("deleteFailed"));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={t("delete")} title={t("delete")}>
            <Trash2 className="size-4 text-destructive" />
          </Button>
        }
      />
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("deleteConfirmTitle")}</AlertDialogTitle>
          <AlertDialogDescription>{t("deleteConfirmDescription", { name })}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{tCommon("cancel")}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={isDeleting} onClick={handleConfirm}>
            {t("delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
