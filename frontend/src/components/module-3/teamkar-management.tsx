"use client";

// module-3's "TeamKar" screen: every app user, with one checkbox each to
// mark them as a member of TeamKar — modeled on the super admin's "Manage
// Access" table (see access-management.tsx), just with a single "member"
// column instead of one column per module. Each checkbox saves immediately,
// sending the whole new set of member ids (see setTeamKarMembers), the same
// "send everything" replace-all pattern used throughout this app.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { ApiError, setTeamKarMembers } from "@/lib/api";
import type { TeamKarUser } from "@/lib/types";
import { Checkbox } from "@/components/ui/checkbox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface TeamKarManagementProps {
  initialUsers: TeamKarUser[];
}

export function TeamKarManagement({ initialUsers }: TeamKarManagementProps) {
  const t = useTranslations("interventionRequests.teamkar");

  const [users, setUsers] = useState(initialUsers);
  // Tracks which single checkbox is mid-request, so we can disable just
  // that one instead of freezing the whole table.
  const [pendingUserId, setPendingUserId] = useState<number | null>(null);

  async function handleToggleMember(user: TeamKarUser, isChecked: boolean) {
    setPendingUserId(user.user_id);

    // Work out the new, complete list of member ids TeamKar should have
    // (the PUT endpoint always expects the full set, not just the one
    // that changed).
    const currentMemberIds = users.filter((current) => current.is_member).map((current) => current.user_id);
    const newMemberIds = isChecked
      ? [...currentMemberIds, user.user_id]
      : currentMemberIds.filter((id) => id !== user.user_id);

    try {
      const updatedUsers = await setTeamKarMembers(newMemberIds);
      setUsers(updatedUsers);
      toast.success(t("membersUpdated"));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("membersUpdateFailed");
      toast.error(message);
    } finally {
      setPendingUserId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="font-bold underline">{t("columnName")}</TableHead>
              <TableHead className="font-bold underline">{t("columnEmail")}</TableHead>
              <TableHead className="text-center font-bold underline">{t("columnMember")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.map((user) => (
              <TableRow key={user.user_id}>
                <TableCell className="font-medium">{user.display_name}</TableCell>
                <TableCell className="text-muted-foreground">{user.email}</TableCell>
                <TableCell className="text-center">
                  <Checkbox
                    checked={user.is_member}
                    disabled={pendingUserId === user.user_id}
                    onCheckedChange={(checked) => handleToggleMember(user, checked === true)}
                    aria-label={`${t("columnMember")} – ${user.display_name}`}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
