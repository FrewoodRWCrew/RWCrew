"use client";

// Altsien Select's "Roles" screen: create/rename/delete custom
// roles, and edit each role's permission matrix (view/create/edit/delete
// per screen). User management lives on its own separate screen — see
// users-management.tsx — gated independently via its own
// "altsienselect.users" permission. Direct mirror of MasterData's
// roles-management.tsx (see docs/module-custom-roles-pattern.md).

import { useState } from "react";
import { KeyRound, Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ApiError,
  createAltsienSelectRole,
  deleteAltsienSelectRole,
  renameAltsienSelectRole,
  setAltsienSelectRolePermissions,
} from "@/lib/api";
import type { AltsienSelectRole, AltsienSelectScreen, AltsienSelectScreenPermission } from "@/lib/types";
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
import { Checkbox } from "@/components/ui/checkbox";
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

interface RolesManagementProps {
  initialScreens: AltsienSelectScreen[];
  initialRoles: AltsienSelectRole[];
}

export function RolesManagement({ initialScreens, initialRoles }: RolesManagementProps) {
  const t = useTranslations("altsienSelect.roles");
  const [screens] = useState(initialScreens);
  const [roles, setRoles] = useState(initialRoles);

  function upsertRole(updatedRole: AltsienSelectRole) {
    setRoles((current) => {
      const exists = current.some((role) => role.id === updatedRole.id);
      return exists
        ? current.map((role) => (role.id === updatedRole.id ? updatedRole : role))
        : [...current, updatedRole].sort((a, b) => a.name.localeCompare(b.name));
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <CreateRoleDialog onCreated={upsertRole} />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("tableName")}</TableHead>
              <TableHead className="sticky top-0 right-0 z-30 bg-background text-right font-bold underline">
                {t("tableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {roles.map((role) => (
              <TableRow key={role.id} className="group">
                <TableCell className="font-medium">{role.name}</TableCell>
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <EditPermissionsDialog role={role} screens={screens} onSaved={upsertRole} />
                    <RenameRoleDialog role={role} onRenamed={upsertRole} />
                    <DeleteRoleAlertDialog
                      role={role}
                      onDeleted={(roleId) => setRoles((current) => current.filter((r) => r.id !== roleId))}
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

interface CreateRoleDialogProps {
  onCreated: (role: AltsienSelectRole) => void;
}

function CreateRoleDialog({ onCreated }: CreateRoleDialogProps) {
  const t = useTranslations("altsienSelect.roles");
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState("");

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const newRole = await createAltsienSelectRole(name);
      toast.success(t("roleCreated"));
      onCreated(newRole);
      setIsOpen(false);
      setName("");
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("createRoleFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger render={<Button>{t("newRole")}</Button>} />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("createRoleTitle")}</DialogTitle>
          <DialogDescription>{t("createRoleDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor="new-role-name">{t("nameLabel")}</Label>
          <Input id="new-role-name" value={name} onChange={(event) => setName(event.target.value)} />
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !name}>
            {t("newRole")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface RenameRoleDialogProps {
  role: AltsienSelectRole;
  onRenamed: (role: AltsienSelectRole) => void;
}

function RenameRoleDialog({ role, onRenamed }: RenameRoleDialogProps) {
  const t = useTranslations("altsienSelect.roles");
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState(role.name);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) setName(role.name);
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const updatedRole = await renameAltsienSelectRole(role.id, name);
      toast.success(t("roleRenamed"));
      onRenamed(updatedRole);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("renameRoleFailed");
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
          <DialogTitle>{t("renameRoleTitle")}</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          <Label htmlFor={`rename-role-${role.id}`}>{t("nameLabel")}</Label>
          <Input id={`rename-role-${role.id}`} value={name} onChange={(event) => setName(event.target.value)} />
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

interface DeleteRoleAlertDialogProps {
  role: AltsienSelectRole;
  onDeleted: (roleId: number) => void;
}

function DeleteRoleAlertDialog({ role, onDeleted }: DeleteRoleAlertDialogProps) {
  const t = useTranslations("altsienSelect.roles");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteAltsienSelectRole(role.id);
      toast.success(t("roleDeleted"));
      onDeleted(role.id);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("deleteRoleFailed");
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
          <AlertDialogDescription>{t("deleteConfirmDescription", { name: role.name })}</AlertDialogDescription>
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

interface EditPermissionsDialogProps {
  role: AltsienSelectRole;
  screens: AltsienSelectScreen[];
  onSaved: (role: AltsienSelectRole) => void;
}

function EditPermissionsDialog({ role, screens, onSaved }: EditPermissionsDialogProps) {
  const t = useTranslations("altsienSelect.roles");
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [permissionsByScreenId, setPermissionsByScreenId] = useState<
    Map<number, AltsienSelectScreenPermission>
  >(new Map());

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the role's latest known permissions each time the
      // dialog is opened, so a screen added since the page loaded (or a
      // change made elsewhere) is never silently overwritten with stale data.
      setPermissionsByScreenId(new Map(role.permissions.map((permission) => [permission.screen_id, permission])));
    }
  }

  function toggle(screenId: number, action: "can_view" | "can_create" | "can_edit" | "can_delete", checked: boolean) {
    setPermissionsByScreenId((current) => {
      const next = new Map(current);
      const screen = screens.find((s) => s.id === screenId);
      const existing = next.get(screenId) ?? {
        screen_id: screenId,
        screen_key: screen?.key ?? "",
        screen_label: screen?.label ?? "",
        can_view: false,
        can_create: false,
        can_edit: false,
        can_delete: false,
      };
      next.set(screenId, { ...existing, [action]: checked });
      return next;
    });
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const updatedRole = await setAltsienSelectRolePermissions(
        role.id,
        screens.map((screen) => {
          const permission = permissionsByScreenId.get(screen.id);
          return {
            screen_id: screen.id,
            can_view: permission?.can_view ?? false,
            can_create: permission?.can_create ?? false,
            can_edit: permission?.can_edit ?? false,
            can_delete: permission?.can_delete ?? false,
          };
        }),
      );
      toast.success(t("permissionsSaved"));
      onSaved(updatedRole);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("permissionsSaveFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <Button variant="ghost" size="icon" aria-label={t("permissions")} title={t("permissions")}>
            <KeyRound className="size-4" />
          </Button>
        }
      />
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("permissionsTitle", { name: role.name })}</DialogTitle>
          <DialogDescription>{t("permissionsDescription")}</DialogDescription>
        </DialogHeader>

        <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("screenColumn")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-center font-bold underline">{t("viewColumn")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-center font-bold underline">{t("createColumn")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-center font-bold underline">{t("editColumn")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-center font-bold underline">{t("deleteColumn")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {screens.map((screen) => {
                const permission = permissionsByScreenId.get(screen.id);
                return (
                  <TableRow key={screen.id}>
                    <TableCell className="font-medium">{screen.label}</TableCell>
                    {(["can_view", "can_create", "can_edit", "can_delete"] as const).map((action) => (
                      <TableCell key={action} className="text-center">
                        <Checkbox
                          checked={permission?.[action] ?? false}
                          onCheckedChange={(checked) => toggle(screen.id, action, checked === true)}
                          aria-label={`${action} – ${screen.label}`}
                        />
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting}>
            {t("permissions")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
