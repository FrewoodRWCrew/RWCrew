"use client";

// Ploeg Wizard step 4: special requests / comments for the organisation.
// Each request is saved straight away (no draft) and gets a status the
// organisation follows up on (New → In Progress → Completed, see the
// Request statuses screen). While a request is still in its first status
// the Kernlid can change or withdraw it; after that it's read-only here and
// shows the organisation's answer.

import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ApiError,
  createAltsienSelectRequest,
  deleteAltsienSelectRequest,
  updateAltsienSelectRequest,
} from "@/lib/api";
import type { AltsienSelectSpecialRequest } from "@/lib/types";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RequestStatusBadge } from "@/components/module-8/request-status-badge";
import { formatDate } from "@/components/module-8/wizard/format";
import type { WizardStepProps } from "@/components/module-8/wizard/step-types";

export function SpecialRequestsStep({ state, teamId, seasonId, readOnly, onStateChange }: WizardStepProps) {
  const t = useTranslations("altsienSelect.steps.special_requests");

  // Keep the wizard's state in sync after each change (newest first).
  function replaceRequests(requests: AltsienSelectSpecialRequest[]) {
    onStateChange({ ...state, requests });
  }

  return (
    <div className="flex flex-col gap-3">
      {!readOnly && (
        <div>
          <RequestFormDialog
            trigger={
              <Button variant="outline">
                <Plus className="size-4" />
                {t("add")}
              </Button>
            }
            onSubmit={async (text) => {
              const created = await createAltsienSelectRequest(teamId, seasonId, text);
              replaceRequests([created, ...state.requests]);
            }}
          />
        </div>
      )}

      {state.requests.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("empty")}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {state.requests.map((request) => (
            <li key={request.id} className="flex flex-col gap-2 rounded-md border p-3">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm whitespace-pre-wrap">{request.text}</p>
                <div className="flex shrink-0 items-center gap-1">
                  <RequestStatusBadge name={request.status_name} color={request.status_color} />
                  {request.editable_by_me && !readOnly && (
                    <>
                      <RequestFormDialog
                        request={request}
                        trigger={
                          <Button variant="ghost" size="icon" aria-label={t("edit")} title={t("edit")}>
                            <Pencil className="size-4" />
                          </Button>
                        }
                        onSubmit={async (text) => {
                          const updated = await updateAltsienSelectRequest(teamId, request.id, text);
                          replaceRequests(state.requests.map((item) => (item.id === updated.id ? updated : item)));
                        }}
                      />
                      <DeleteRequestDialog
                        onConfirm={async () => {
                          await deleteAltsienSelectRequest(teamId, request.id);
                          replaceRequests(state.requests.filter((item) => item.id !== request.id));
                        }}
                      />
                    </>
                  )}
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {t("createdBy", { name: request.created_by_name ?? "—", date: formatDate(request.created_at) })}
              </p>
              {request.organisation_note && (
                <p className="rounded bg-muted px-2 py-1 text-sm">
                  <span className="font-medium">{t("organisationNote")}:</span> {request.organisation_note}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface RequestFormDialogProps {
  request?: AltsienSelectSpecialRequest;
  trigger: React.ReactElement;
  onSubmit: (text: string) => Promise<void>;
}

/** Add or change one request's text. */
function RequestFormDialog({ request, trigger, onSubmit }: RequestFormDialogProps) {
  const t = useTranslations("altsienSelect.steps.special_requests");
  const [isOpen, setIsOpen] = useState(false);
  const [text, setText] = useState(request?.text ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    // Start from the request's current text each time.
    if (open) setText(request?.text ?? "");
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      await onSubmit(text.trim());
      toast.success(request ? t("updated") : t("created"));
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
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{request ? t("editTitle") : t("addTitle")}</DialogTitle>
          <DialogDescription>{t("dialogDescription")}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <Label htmlFor="altsien-request-text">{t("textLabel")}</Label>
          <Textarea
            id="altsien-request-text"
            rows={5}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !text.trim()}>
            {request ? t("save") : t("add")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Confirm withdrawing a request. */
function DeleteRequestDialog({ onConfirm }: { onConfirm: () => Promise<void> }) {
  const t = useTranslations("altsienSelect.steps.special_requests");
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
          <AlertDialogDescription>{t("deleteConfirmDescription")}</AlertDialogDescription>
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
