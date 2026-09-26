"use client";

// The organisation's "Opvolging aanvragen" screen: every special request of
// the season across all teams, oldest first, filterable by status. The
// pencil opens a dialog to set the request's status (New / In Progress /
// Completed, see the Request statuses screen) and write an answer the
// Kernlid then sees in the wizard and on the Ploegfiche. Follows the app's
// list-screen table pattern (pinned header + Actions column, capped scroll).

import { useState } from "react";
import { Pencil } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, followUpAltsienSelectRequest, listAltsienSelectFollowUpRequests } from "@/lib/api";
import type { AltsienSelectRequestStatus, AltsienSelectSpecialRequest, Season } from "@/lib/types";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { AltsienSeasonSelect, useAltsienSeasonId } from "@/components/module-8/altsien-season-select";
import { RequestStatusBadge } from "@/components/module-8/request-status-badge";
import { useKeyedLoad } from "@/components/module-8/use-keyed-load";
import { formatDate } from "@/components/module-8/wizard/format";

// Base UI's Select needs a real string value for "all statuses".
const ALL_STATUSES = "all";

interface RequestFollowUpProps {
  seasons: Season[];
  statuses: AltsienSelectRequestStatus[];
}

export function RequestFollowUp({ seasons, statuses }: RequestFollowUpProps) {
  const t = useTranslations("altsienSelect.followUp");
  const seasonId = useAltsienSeasonId(seasons);
  const [statusFilter, setStatusFilter] = useState<string>(ALL_STATUSES);
  const requests = useKeyedLoad<AltsienSelectSpecialRequest[]>(seasonId === null ? null : String(seasonId), () =>
    listAltsienSelectFollowUpRequests(seasonId as number),
  );

  const visible = (requests.data ?? []).filter(
    (request) => statusFilter === ALL_STATUSES || String(request.status_id) === statusFilter,
  );

  function replace(updated: AltsienSelectSpecialRequest) {
    requests.setData((requests.data ?? []).map((item) => (item.id === updated.id ? updated : item)));
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex w-48 flex-col gap-2">
            <Label htmlFor="follow-up-status">{t("statusFilter")}</Label>
            <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value ?? ALL_STATUSES)}>
              <SelectTrigger id="follow-up-status">
                <SelectValue>
                  {(value: string | null) =>
                    statuses.find((item) => String(item.id) === value)?.name ?? t("allStatuses")
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_STATUSES}>{t("allStatuses")}</SelectItem>
                {statuses.map((item) => (
                  <SelectItem key={item.id} value={String(item.id)}>
                    {item.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <AltsienSeasonSelect seasons={seasons} seasonId={seasonId} />
        </div>
      </div>

      {seasonId === null && <p className="text-sm text-muted-foreground">{t("noSeason")}</p>}
      {requests.isLoading && <p className="text-sm text-muted-foreground">{t("loading")}</p>}
      {requests.failed && <p className="text-sm text-destructive">{t("loadError")}</p>}
      {requests.data && visible.length === 0 && <p className="text-sm text-muted-foreground">{t("empty")}</p>}

      {visible.length > 0 && (
        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("columnTeam")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                  {t("columnRequest")}
                </TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                  {t("columnSubmitted")}
                </TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                  {t("columnStatus")}
                </TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                  {t("columnNote")}
                </TableHead>
                <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                  {t("columnActions")}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visible.map((request) => (
                <TableRow key={request.id} className="group">
                  <TableCell className="font-medium">{request.team_name}</TableCell>
                  <TableCell className="max-w-md whitespace-pre-wrap">{request.text}</TableCell>
                  <TableCell className="text-muted-foreground">
                    <div className="flex flex-col">
                      <span>{request.created_by_name ?? "—"}</span>
                      <span className="text-xs tabular-nums">{formatDate(request.created_at)}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <RequestStatusBadge name={request.status_name} color={request.status_color} />
                  </TableCell>
                  <TableCell className="max-w-xs whitespace-pre-wrap text-muted-foreground">
                    {request.organisation_note ?? "—"}
                  </TableCell>
                  {/* Saving needs "edit" on the follow-up screen; the backend enforces it. */}
                  <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                    <div className="flex justify-end">
                      <FollowUpDialog request={request} statuses={statuses} onSaved={replace} />
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

interface FollowUpDialogProps {
  request: AltsienSelectSpecialRequest;
  statuses: AltsienSelectRequestStatus[];
  onSaved: (request: AltsienSelectSpecialRequest) => void;
}

/** Set one request's status and the organisation's answer. */
function FollowUpDialog({ request, statuses, onSaved }: FollowUpDialogProps) {
  const t = useTranslations("altsienSelect.followUp");
  const [isOpen, setIsOpen] = useState(false);
  const [statusId, setStatusId] = useState(String(request.status_id));
  const [note, setNote] = useState(request.organisation_note ?? "");
  const [isSaving, setIsSaving] = useState(false);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    // Start from the request's current values each time.
    if (open) {
      setStatusId(String(request.status_id));
      setNote(request.organisation_note ?? "");
    }
  }

  async function handleSave() {
    setIsSaving(true);
    try {
      const saved = await followUpAltsienSelectRequest(request.id, {
        status_id: Number(statusId),
        organisation_note: note.trim() || null,
      });
      onSaved(saved);
      toast.success(t("saved"));
      setIsOpen(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("saveFailed"));
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={t("edit")} title={t("edit")}>
            <Pencil className="size-4" />
          </Button>
        }
      />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("editTitle", { team: request.team_name })}</DialogTitle>
          <DialogDescription className="whitespace-pre-wrap">{request.text}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="follow-up-edit-status">{t("columnStatus")}</Label>
            <Select value={statusId} onValueChange={(value) => value && setStatusId(value)}>
              <SelectTrigger id="follow-up-edit-status">
                <SelectValue>
                  {(value: string | null) => statuses.find((item) => String(item.id) === value)?.name ?? ""}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {statuses.map((item) => (
                  <SelectItem key={item.id} value={String(item.id)}>
                    {item.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="follow-up-edit-note">{t("columnNote")}</Label>
            <Textarea id="follow-up-edit-note" rows={4} value={note} onChange={(event) => setNote(event.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={handleSave} disabled={isSaving}>
            {t("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
