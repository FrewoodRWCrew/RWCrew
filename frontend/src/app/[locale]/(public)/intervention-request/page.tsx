// The old address of the public intervention form. Karbladen printed before
// the public kar page existed have this in their QR code, so it now sends the
// team to the kar page (/kar, two tiles: intervention + Kar inventaris) with
// the same query string; the form itself lives at /kar/intervention-request.

import { redirect } from "@/i18n/navigation";
import { karQrQuery, type RawSearchParams } from "@/lib/kar-qr-params";

interface OldInterventionRequestPageProps {
  params: Promise<{ locale: string }>;
  searchParams: Promise<RawSearchParams>;
}

export default async function OldInterventionRequestPage({ params, searchParams }: OldInterventionRequestPageProps) {
  const { locale } = await params;
  redirect({ href: `/kar${karQrQuery(await searchParams)}`, locale });
}
