"use client";

// The super admin's "Season" master-data screen: a simple table of
// seasons with add/change/delete, following the exact same dialog/table
// pattern as the "Manage Access" user table (see access-management.tsx).

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createSeason, deleteSeason, updateSeason } from "@/lib/api";
import type { Season } from "@/lib/types";
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface SeasonManagementProps {
  initialSeasons: Season[];
}

export function SeasonManagement({ initialSeasons }: SeasonManagementProps) {
  const t = useTranslations("admin.masterData.season");
  const router = useRouter();

  // Kept in local state so create/change/delete update the table
  // instantly, without waiting for a full page reload.
  const [seasons, setSeasons] = useState(initialSeasons);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">{t("title")}</h2>
          <p className="text-sm text-muted-foreground">{t("description")}</p>
        </div>
        <CreateSeasonDialog
          onCreated={(newSeason) => {
            setSeasons((current) => [...current, newSeason].sort((a, b) => a.name.localeCompare(b.name)));
            router.refresh();
          }}
        />
      </div>

      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("tableName")}</TableHead>
              <TableHead className="text-right">{t("tableActions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {seasons.map((season) => (
              <TableRow key={season.id}>
                <TableCell className="font-medium">{season.name}</TableCell>
                <TableCell>
                  <div className="flex justify-end gap-1">
                    <ChangeSeasonDialog
                      season={season}
                      onChanged={(updatedSeason) => {
                        setSeasons((current) =>
                          current
                            .map((item) => (item.id === updatedSeason.id ? updatedSeason : item))
                            .sort((a, b) => a.name.localeCompare(b.name)),
                        );
                        router.refresh();
                      }}
                    />
                    <DeleteSeasonAlertDialog
                      season={season}
                      onDeleted={(deletedSeasonId) => {
                        setSeasons((current) => current.filter((item) => item.id !== deletedSeasonId));
                        router.refresh();
                      }}
                    />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

interface CreateSeasonDialogProps {
  onCreated: (season: Season) => void;
}

function CreateSeasonDialog({ onCreated }: CreateSeasonDialogProps) {
  const t = useTranslations("admin.masterData.season");
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState("");

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const newSeason = await createSeason(name);
      toast.success(t("seasonCreated"));
      onCreated(newSeason);
      setIsOpen(false);
      setName("");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("createFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger render={<Button>{t("newSeason")}</Button>} />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("createTitle")}</DialogTitle>
          <DialogDescription>{t("createDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor="new-season-name">{t("nameLabel")}</Label>
          <Input id="new-season-name" value={name} onChange={(event) => setName(event.target.value)} />
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !name}>
            {t("newSeason")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface ChangeSeasonDialogProps {
  season: Season;
  onChanged: (season: Season) => void;
}

function ChangeSeasonDialog({ season, onChanged }: ChangeSeasonDialogProps) {
  const t = useTranslations("admin.masterData.season");
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState(season.name);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the season's latest known name each time the dialog
      // is opened, in case it changed since last time.
      setName(season.name);
    }
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const updatedSeason = await updateSeason(season.id, name);
      toast.success(t("seasonUpdated"));
      onChanged(updatedSeason);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("updateFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={t("change")} title={t("change")}>
            <Pencil className="size-4" />
          </Button>
        }
      />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("changeTitle")}</DialogTitle>
          <DialogDescription>{t("changeDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor={`change-season-name-${season.id}`}>{t("nameLabel")}</Label>
          <Input
            id={`change-season-name-${season.id}`}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !name}>
            {t("change")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteSeasonAlertDialogProps {
  season: Season;
  onDeleted: (seasonId: number) => void;
}

function DeleteSeasonAlertDialog({ season, onDeleted }: DeleteSeasonAlertDialogProps) {
  const t = useTranslations("admin.masterData.season");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteSeason(season.id);
      toast.success(t("seasonDeleted"));
      onDeleted(season.id);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("deleteFailed");
      toast.error(message);
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: season.name })}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{tCommon("cancel")}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={isDeleting} onClick={handleConfirmDelete}>
            {t("delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
