"use client";

// The super admin's "Manage Access" screen: a table with one row per
// user (with phone, Super admin and Altsien Kernlid flags) and one
// checkbox per module, plus buttons to create, change, and
// delete user accounts. This is the ONLY place module access is granted
// or revoked — see backend/app/landing/admin.py for the matching API
// endpoints.

import { useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { useRouter } from "@/i18n/navigation";
import { ApiError, createUser, deleteUser, setUserModuleAccess, updateUser } from "@/lib/api";
import type { ModuleInfo, UserSummary } from "@/lib/types";
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

interface AccessManagementProps {
  initialUsers: UserSummary[];
  modules: ModuleInfo[];
  // The logged-in super admin — their own Super admin box is locked so they
  // can't remove their own access (the backend refuses it too).
  currentUserId: number;
}

export function AccessManagement({ initialUsers, modules, currentUserId }: AccessManagementProps) {
  const t = useTranslations("admin.access");
  const router = useRouter();

  // The user list is kept in local state so a checkbox, edit, or delete
  // can update the table instantly, without waiting for a full page reload.
  const [users, setUsers] = useState(initialUsers);
  // Tracks which single checkbox is mid-request, so we can disable just
  // that one instead of freezing the whole table.
  const [pendingCheckbox, setPendingCheckbox] = useState<string | null>(null);

  const sortedModules = [...modules].sort((a, b) => a.sort_order - b.sort_order);

  async function handleToggleAccess(user: UserSummary, moduleKey: string, isChecked: boolean) {
    const checkboxId = `${user.id}:${moduleKey}`;
    setPendingCheckbox(checkboxId);

    // Work out the new, complete list of modules this user should have
    // access to (see SetUserAccessRequest in the backend: it always
    // expects the full list, not just the one that changed).
    const newModuleKeys = isChecked
      ? [...user.accessible_module_keys, moduleKey]
      : user.accessible_module_keys.filter((key) => key !== moduleKey);

    try {
      const updatedUser = await setUserModuleAccess(user.id, newModuleKeys);
      setUsers((currentUsers) => currentUsers.map((current) => (current.id === user.id ? updatedUser : current)));
      toast.success(t("accessUpdated"));
    } catch {
      toast.error(t("accessUpdateFailed"));
    } finally {
      setPendingCheckbox(null);
    }
  }

  // Saves one of the two flags immediately, like the module checkboxes do.
  async function handleToggleFlag(
    user: UserSummary,
    flag: "is_super_admin" | "is_altsien_kernlid",
    isChecked: boolean,
  ) {
    setPendingCheckbox(`${user.id}:${flag}`);
    try {
      const updatedUser = await updateUser(user.id, { [flag]: isChecked });
      setUsers((currentUsers) => currentUsers.map((current) => (current.id === user.id ? updatedUser : current)));
      toast.success(t("detailsUpdated"));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : t("detailsUpdateFailed"));
    } finally {
      setPendingCheckbox(null);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <CreateUserDialog
          onCreated={(newUser) => {
            setUsers((currentUsers) => [...currentUsers, newUser]);
            router.refresh();
          }}
        />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background align-bottom pb-3 font-bold underline">{t("userTableName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background align-bottom pb-3 font-bold underline">{t("userTableEmail")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background align-bottom pb-3 font-bold underline">{t("userTablePhone")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-center align-bottom pb-3 font-bold underline">{t("userTableSuperAdmin")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background text-center align-bottom pb-3 font-bold underline">{t("userTableAltsienKernlid")}</TableHead>
              {sortedModules.map((module) => (
                <TableHead
                  key={module.key}
                  className="sticky top-0 z-20 h-32 bg-background text-center align-bottom pb-3 font-bold underline"
                >
                  {/* writing-mode lays the text out in a column exactly as
                      wide as the vertical text itself, so it's centered
                      directly above this same column's checkboxes below —
                      a rotate() transform on horizontal text does NOT do
                      this, since its layout box stays as wide as the
                      un-rotated text and can drift off-center. rotate-180
                      flips the vertical-rl default (top-to-bottom) so the
                      text reads bottom-to-top instead, matching the usual
                      spreadsheet column-header convention. */}
                  <div className="inline-block [writing-mode:vertical-rl] rotate-180 whitespace-nowrap">
                    {module.name}
                  </div>
                </TableHead>
              ))}
              <TableHead className="sticky top-0 right-0 z-30 bg-background align-bottom pb-3 text-right font-bold underline">
                {t("userTableActions")}
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.id} className="group">
                <TableCell className="font-medium">{user.display_name}</TableCell>
                <TableCell className="text-muted-foreground">{user.email}</TableCell>
                <TableCell className="text-muted-foreground">{user.phone}</TableCell>
                <TableCell className="text-center">
                  <Checkbox
                    checked={user.is_super_admin}
                    disabled={user.id === currentUserId || pendingCheckbox === `${user.id}:is_super_admin`}
                    onCheckedChange={(checked) => handleToggleFlag(user, "is_super_admin", checked === true)}
                    aria-label={`${t("superAdminLabel")} – ${user.display_name}`}
                  />
                </TableCell>
                <TableCell className="text-center">
                  <Checkbox
                    checked={user.is_altsien_kernlid}
                    disabled={pendingCheckbox === `${user.id}:is_altsien_kernlid`}
                    onCheckedChange={(checked) => handleToggleFlag(user, "is_altsien_kernlid", checked === true)}
                    aria-label={`${t("altsienKernlidLabel")} – ${user.display_name}`}
                  />
                </TableCell>
                {sortedModules.map((module) => {
                  const checkboxId = `${user.id}:${module.key}`;
                  return (
                    <TableCell key={module.key} className="text-center">
                      <Checkbox
                        checked={user.accessible_module_keys.includes(module.key)}
                        disabled={pendingCheckbox === checkboxId}
                        onCheckedChange={(checked) => handleToggleAccess(user, module.key, checked === true)}
                        aria-label={`${module.name} – ${user.display_name}`}
                      />
                    </TableCell>
                  );
                })}
                <TableCell className="sticky right-0 z-10 bg-background group-hover:bg-muted/50">
                  <div className="flex justify-end gap-1">
                    <ChangeAccessDialog
                      user={user}
                      modules={sortedModules}
                      isSelf={user.id === currentUserId}
                      onUpdated={(updatedUser) => {
                        setUsers((currentUsers) =>
                          currentUsers.map((current) => (current.id === updatedUser.id ? updatedUser : current)),
                        );
                      }}
                    />
                    <DeleteUserAlertDialog
                      user={user}
                      onDeleted={(deletedUserId) => {
                        setUsers((currentUsers) => currentUsers.filter((current) => current.id !== deletedUserId));
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

interface CreateUserDialogProps {
  onCreated: (user: UserSummary) => void;
}

function CreateUserDialog({ onCreated }: CreateUserDialogProps) {
  const t = useTranslations("admin.access");
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [isSuperAdmin, setIsSuperAdmin] = useState(false);
  const [isAltsienKernlid, setIsAltsienKernlid] = useState(false);

  function resetForm() {
    setDisplayName("");
    setEmail("");
    setPassword("");
    setPhone("");
    setIsSuperAdmin(false);
    setIsAltsienKernlid(false);
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const newUser = await createUser({
        display_name: displayName,
        email,
        password,
        is_super_admin: isSuperAdmin,
        is_altsien_kernlid: isAltsienKernlid,
        phone: phone.trim() || null,
      });
      toast.success(t("userCreated"));
      onCreated(newUser);
      setIsOpen(false);
      resetForm();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("createUserFailed");
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger render={<Button>{t("newUser")}</Button>} />
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("createUserTitle")}</DialogTitle>
          <DialogDescription>{t("createUserDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-user-name">{t("displayNameLabel")}</Label>
            <Input id="new-user-name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-user-email">{t("emailLabel")}</Label>
            <Input
              id="new-user-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-user-password">{t("passwordLabel")}</Label>
            <Input
              id="new-user-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="new-user-phone">{t("phoneLabel")}</Label>
            <Input id="new-user-phone" type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} />
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="new-user-super-admin"
              checked={isSuperAdmin}
              onCheckedChange={(checked) => setIsSuperAdmin(checked === true)}
            />
            <Label htmlFor="new-user-super-admin">{t("superAdminLabel")}</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="new-user-altsien-kernlid"
              checked={isAltsienKernlid}
              onCheckedChange={(checked) => setIsAltsienKernlid(checked === true)}
            />
            <Label htmlFor="new-user-altsien-kernlid">{t("altsienKernlidLabel")}</Label>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !displayName || !email || !password}>
            {t("newUser")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface ChangeAccessDialogProps {
  user: UserSummary;
  modules: ModuleInfo[];
  // True when this row is the logged-in super admin: their Super admin box is locked.
  isSelf: boolean;
  onUpdated: (user: UserSummary) => void;
}

function ChangeAccessDialog({ user, modules, isSelf, onUpdated }: ChangeAccessDialogProps) {
  const t = useTranslations("admin.access");
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  // The set of module keys checked in the dialog right now. This is a
  // separate, local copy of the user's real access — nothing is saved
  // until "Change" is clicked, so ticking several boxes only takes one
  // request instead of one per checkbox (unlike the table's checkboxes,
  // which save immediately).
  const [selectedModuleKeys, setSelectedModuleKeys] = useState<string[]>(user.accessible_module_keys);
  // Same idea for the phone number and the two flags: local until "Change".
  const [phone, setPhone] = useState(user.phone ?? "");
  const [isSuperAdmin, setIsSuperAdmin] = useState(user.is_super_admin);
  const [isAltsienKernlid, setIsAltsienKernlid] = useState(user.is_altsien_kernlid);
  // Optional new password (an admin reset); empty means "keep the current one".
  const [newPassword, setNewPassword] = useState("");

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from the user's latest known access each time the dialog
      // is opened, in case it changed since last time (e.g. via the
      // table's own checkboxes).
      setSelectedModuleKeys(user.accessible_module_keys);
      setPhone(user.phone ?? "");
      setIsSuperAdmin(user.is_super_admin);
      setIsAltsienKernlid(user.is_altsien_kernlid);
      setNewPassword("");
    }
  }

  function toggleModule(moduleKey: string, isChecked: boolean) {
    setSelectedModuleKeys((current) =>
      isChecked ? [...current, moduleKey] : current.filter((key) => key !== moduleKey),
    );
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      // Only send the details request if something in it actually changed.
      const newPhone = phone.trim() || null;
      const detailsChanged =
        newPhone !== user.phone ||
        isSuperAdmin !== user.is_super_admin ||
        isAltsienKernlid !== user.is_altsien_kernlid ||
        newPassword !== "";
      if (detailsChanged) {
        await updateUser(user.id, {
          phone: newPhone,
          is_super_admin: isSuperAdmin,
          is_altsien_kernlid: isAltsienKernlid,
          // Only sent when filled in, so an empty box never touches the password.
          ...(newPassword !== "" ? { password: newPassword } : {}),
        });
      }
      const updatedUser = await setUserModuleAccess(user.id, selectedModuleKeys);
      toast.success(newPassword !== "" ? t("passwordReset") : t("accessUpdated"));
      onUpdated(updatedUser);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("accessUpdateFailed");
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
          <DialogTitle>{t("changeAccessTitle", { name: user.display_name })}</DialogTitle>
          <DialogDescription>{t("changeAccessDescription", { name: user.display_name })}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor={`change-phone-${user.id}`}>{t("phoneLabel")}</Label>
            <Input
              id={`change-phone-${user.id}`}
              type="tel"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`change-password-${user.id}`}>{t("newPasswordLabel")}</Label>
            <Input
              id={`change-password-${user.id}`}
              type="password"
              autoComplete="new-password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
            />
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id={`change-super-admin-${user.id}`}
              checked={isSuperAdmin}
              disabled={isSelf}
              onCheckedChange={(checked) => setIsSuperAdmin(checked === true)}
            />
            <Label htmlFor={`change-super-admin-${user.id}`}>{t("superAdminLabel")}</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id={`change-altsien-kernlid-${user.id}`}
              checked={isAltsienKernlid}
              onCheckedChange={(checked) => setIsAltsienKernlid(checked === true)}
            />
            <Label htmlFor={`change-altsien-kernlid-${user.id}`}>{t("altsienKernlidLabel")}</Label>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          {modules.map((module) => {
            const checkboxId = `change-access-${user.id}-${module.key}`;
            return (
              <div key={module.key} className="flex items-center gap-2">
                <Checkbox
                  id={checkboxId}
                  checked={selectedModuleKeys.includes(module.key)}
                  onCheckedChange={(checked) => toggleModule(module.key, checked === true)}
                />
                <Label htmlFor={checkboxId}>{module.name}</Label>
              </div>
            );
          })}
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || (newPassword !== "" && newPassword.length < 8)}>
            {t("change")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface DeleteUserAlertDialogProps {
  user: UserSummary;
  onDeleted: (userId: number) => void;
}

function DeleteUserAlertDialog({ user, onDeleted }: DeleteUserAlertDialogProps) {
  const t = useTranslations("admin.access");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      await deleteUser(user.id);
      toast.success(t("userDeleted"));
      onDeleted(user.id);
      setIsOpen(false);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("deleteUserFailed");
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
          <AlertDialogDescription>
            {t("deleteConfirmDescription", { name: user.display_name })}
          </AlertDialogDescription>
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
