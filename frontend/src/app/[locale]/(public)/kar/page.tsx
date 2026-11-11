// The public kar page (no login) that the karblad's QR code opens: the kar's
// details and two tiles, "Interventie aanvragen" and "Kar inventaris" (see
// components/shared/kar-qr/kar-qr-landing.tsx). The QR code's query string
// (team_id, cart_number, delivery_location, zone) is read here and passed on.

import { serverApiFetch } from "@/lib/server-api";
import type { InterventionRequestsTeam } from "@/lib/types";
import { readKarQrParams, type RawSearchParams } from "@/lib/kar-qr-params";
import { KarQrLanding } from "@/components/shared/kar-qr/kar-qr-landing";

interface KarPageProps {
  searchParams: Promise<RawSearchParams>;
}

export default async function KarPage({ searchParams }: KarPageProps) {
  const params = readKarQrParams(await searchParams);

  // The team's name for the header; the page still works when the lookup fails.
  let teamName = params.team_name ?? null;
  if (params.team_id) {
    const teams = await serverApiFetch<InterventionRequestsTeam[]>("/api/public/intervention-requests/teams").catch(
      () => [] as InterventionRequestsTeam[],
    );
    teamName = teams.find((team) => team.id === Number(params.team_id))?.name ?? teamName;
  }

  return <KarQrLanding params={params} teamName={teamName} />;
}
