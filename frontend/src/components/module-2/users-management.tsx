"use client";

// KarTracker's "Users" screen: everyone with access to KarTracker, a
// dropdown to change their role, and a "New user" action that can create a
// brand-new account, scoped to KarTracker only. Direct mirror of
// Intervention Requests'/MasterData's users-management.tsx (see
// docs/module-custom-roles-pattern.md).

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, createOrGrantKarTrackerUser, setKarTrackerUserRole } from "@/lib/api";
import type { KarTrackerRole, KarTrackerUserSummary } from "@/lib/types";
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface UsersManagementProps {
  roles: KarTrackerRole[];
  initialUsers: KarTrackerUserSummary[];
}

// The "— none —" option in a role dropdown is represented by this
// string, since shadcn's Select needs every item to have a non-empty value.
const NO_ROLE_VALUE = "none";

export function UsersManagement({ roles, initialUsers }: UsersManagementProps) {
  const t = useTranslations("karTracker.users");
  const [users, setUsers] = useState(initialUsers);

  // Base UI's <Select.Value> shows the raw value string unless told how
  // to turn it into a label — this looks up the matching role's name (or
  // "no role") for whatever value is currently selected.
  function roleLabelFor(value: string | null): string {
    if (!value || value === NO_ROLE_VALUE) return t("noRole");
    return roles.find((role) => String(role.id) === value)?.name ?? t("noRole");
  }

  function upsertUser(updatedUser: KarTrackerUserSummary) {
    setUsers((current) => {
      const exists = current.some((user) => user.user_id === updatedUser.user_id);
      return exists
        ? current.map((user) => (user.user_id === updatedUser.user_id ? updatedUser : user))
        : [...current, updatedUser];
    });
  }

  async function handleChangeUserRole(user: KarTrackerUserSummary, roleIdValue: string) {
    const roleId = roleIdValue === NO_ROLE_VALUE ? null : Number(roleIdValue);
    try {
      const updatedUser = await setKarTrackerUserRole(user.user_id, roleId);
      upsertUser(updatedUser);
      toast.success(t("roleAssigned"));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("roleAssignFailed");
      toast.error(message);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
          <p className="text-muted-foreground">{t("description")}</p>
        </div>
        <CreateOrGrantUserDialog roles={roles} onSaved={upsertUser} />
      </div>

      <div className="rounded-md border [&>div]:max-h-[65vh] [&>div]:overflow-y-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("userTableName")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("userTableEmail")}</TableHead>
              <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("userTableRole")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.user_id}>
                <TableCell className="font-medium">{user.display_name}</TableCell>
                <TableCell className="text-muted-foreground">{user.email}</TableCell>
                <TableCell>
                  <Select
                    value={user.role_id ? String(user.role_id) : NO_ROLE_VALUE}
                    onValueChange={(value) => handleChangeUserRole(user, value ?? NO_ROLE_VALUE)}
                  >
                    <SelectTrigger className="w-48">
                      <SelectValue>{(value: string | null) => roleLabelFor(value)}</SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NO_ROLE_VALUE}>{t("noRole")}</SelectItem>
                      {roles.map((role) => (
                        <SelectItem key={role.id} value={String(role.id)}>
                          {role.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

interface CreateOrGrantUserDialogProps {
  roles: KarTrackerRole[];
  onSaved: (user: KarTrackerUserSummary) => void;
}

function CreateOrGrantUserDialog({ roles, onSaved }: CreateOrGrantUserDialogProps) {
  const t = useTranslations("karTracker.users");
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [roleId, setRoleId] = useState<string>(NO_ROLE_VALUE);

  function resetForm() {
    setEmail("");
    setDisplayName("");
    setPassword("");
    setRoleId(NO_ROLE_VALUE);
  }

  function roleLabelFor(value: string | null): string {
    if (!value || value === NO_ROLE_VALUE) return t("noRole");
    return roles.find((role) => String(role.id) === value)?.name ?? t("noRole");
  }

  async function handleSubmit() {
    setIsSubmitting(true);
    try {
      const savedUser = await createOrGrantKarTrackerUser({
        email,
        display_name: displayName || undefined,
        password: password || undefined,
        role_id: roleId === NO_ROLE_VALUE ? null : Number(roleId),
      });
      toast.success(t("userSaved"));
      onSaved(savedUser);
      setIsOpen(false);
      resetForm();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("userSaveFailed");
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
          <DialogTitle>{t("newUserTitle")}</DialogTitle>
          <DialogDescription>{t("newUserDescription")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Label htmlFor="kartracker-new-user-email">{t("emailLabel")}</Label>
            <Input
              id="kartracker-new-user-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="kartracker-new-user-name">{t("newUserNameLabel")}</Label>
            <Input
              id="kartracker-new-user-name"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="kartracker-new-user-password">{t("newUserPasswordLabel")}</Label>
            <Input
              id="kartracker-new-user-password"
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-2">
            <Label>{t("userTableRole")}</Label>
            <Select value={roleId} onValueChange={(value) => setRoleId(value ?? NO_ROLE_VALUE)}>
              <SelectTrigger>
                <SelectValue>{(value: string | null) => roleLabelFor(value)}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NO_ROLE_VALUE}>{t("noRole")}</SelectItem>
                {roles.map((role) => (
                  <SelectItem key={role.id} value={String(role.id)}>
                    {role.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button onClick={handleSubmit} disabled={isSubmitting || !email}>
            {t("newUser")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
