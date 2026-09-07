"use client";

// The "Ploeg" field: pick an existing MasterData team, or choose "Andere"
// to type a name that isn't in the list yet (see team_name on
// InterventionRequest, app/db/models/intervention_request.py). Used by
// both the staff admin dialog (intervention-requests-management.tsx) and
// the public, no-login intervention-request form
// (public-intervention-request-form.tsx) so "Ploeg not in the list"
// behaves identically everywhere it appears. Deliberately has no fetching
// or translation-namespace opinions of its own — callers pass the teams
// list and every label, so it works the same regardless of who's logged in.

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { InterventionRequestsTeam } from "@/lib/types";

const OTHER_VALUE = "__other__";

interface TeamComboboxProps {
  id: string;
  label: string;
  teams: InterventionRequestsTeam[];
  teamId: number | null;
  teamName: string | null;
  otherOptionLabel: string;
  otherPlaceholder: string;
  onChange: (next: { team_id: number | null; team_name: string | null }) => void;
}

export function TeamCombobox({
  id,
  label,
  teams,
  teamId,
  teamName,
  otherOptionLabel,
  otherPlaceholder,
  onChange,
}: TeamComboboxProps) {
  // Whether "Andere" is the active choice — tracked separately from
  // teamName because right after picking "Andere" the free-text input is
  // still empty, at which point teamName alone can't tell "other, not
  // typed yet" apart from "nothing chosen yet".
  const [isOther, setIsOther] = useState(teamId == null && Boolean(teamName));

  const selectValue = isOther ? OTHER_VALUE : teamId != null ? String(teamId) : "";

  function handleSelect(value: string | null) {
    if (value === null) return;
    if (value === OTHER_VALUE) {
      setIsOther(true);
      onChange({ team_id: null, team_name: teamName ?? "" });
    } else {
      setIsOther(false);
      onChange({ team_id: Number(value), team_name: null });
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Select value={selectValue} onValueChange={handleSelect}>
        <SelectTrigger id={id}>
          <SelectValue>
            {(value: string | null) =>
              value === OTHER_VALUE
                ? otherOptionLabel
                : (teams.find((team) => String(team.id) === value)?.name ?? "")
            }
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {teams.map((team) => (
            <SelectItem key={team.id} value={String(team.id)}>
              {team.name}
            </SelectItem>
          ))}
          <SelectItem value={OTHER_VALUE}>{otherOptionLabel}</SelectItem>
        </SelectContent>
      </Select>
      {isOther && (
        <Input
          id={`${id}-name`}
          placeholder={otherPlaceholder}
          value={teamName ?? ""}
          onChange={(event) => onChange({ team_id: null, team_name: event.target.value })}
        />
      )}
    </div>
  );
}
