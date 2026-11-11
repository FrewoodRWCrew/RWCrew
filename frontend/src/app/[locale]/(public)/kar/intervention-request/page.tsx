// The public, no-login intervention-request form, reached from the public kar
// page's "Interventie aanvragen" tile (karblad QR code → /kar). A sibling route
// group to (protected)/(auth) with no auth-gating layout, so a team member
// without an RWCrew account can use it. The query string (passed on by the
// tile) pre-fills Ploeg/Karnr/Afleverplaats/Zone.

import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { InterventionRequestsTeam } from "@/lib/types";
import { karQrQuery, readKarQrParams, type RawSearchParams } from "@/lib/kar-qr-params";
import { PublicInterventionRequestForm } from "@/components/module-3/public-intervention-request-form";
import { KarQrShell } from "@/components/shared/kar-qr/kar-qr-shell";

interface InterventionRequestPageProps {
  searchParams: Promise<RawSearchParams>;
}

export default async function KarInterventionRequestPage({ searchParams }: InterventionRequestPageProps) {
  const params = readKarQrParams(await searchParams);

  const teams: InterventionRequestsTeam[] = await serverApiFetch<InterventionRequestsTeam[]>(
    "/api/public/intervention-requests/teams",
  ).catch((error) => {
    // The public form should still render (with the "other" free-text
    // Ploeg option) even if the teams lookup itself fails.
    if (error instanceof ServerApiError) return [];
    throw error;
  });

  const parsedTeamId = params.team_id ? Number(params.team_id) : NaN;
  const matchingTeam = teams.find((team) => team.id === parsedTeamId);

  return (
    <KarQrShell karNumber={params.cart_number} backHref={`/kar${karQrQuery(params)}`}>
      <div className="flex justify-center">
        <PublicInterventionRequestForm
          teams={teams}
          defaults={{
            team_id: matchingTeam?.id ?? null,
            team_name: params.team_name ?? null,
            cart_number: params.cart_number ?? null,
            delivery_location: params.delivery_location ?? null,
            zone: params.zone ?? null,
          }}
        />
      </div>
    </KarQrShell>
  );
}
