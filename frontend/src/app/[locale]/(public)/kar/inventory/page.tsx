// "Kar inventaris" (public, no login), reached from the public kar page's tile
// (karblad QR code → /kar): the team types the kar's lock code, then counts
// what is in the kar before it is picked up. Data belongs to StockMaster
// (module-4); the screens live in components/module-4/public-kar-inventory/.

import { karQrQuery, readKarQrParams, type RawSearchParams } from "@/lib/kar-qr-params";
import { KarInventoryFlow } from "@/components/module-4/public-kar-inventory/kar-inventory-flow";
import { KarQrShell } from "@/components/shared/kar-qr/kar-qr-shell";

interface KarInventoryPageProps {
  searchParams: Promise<RawSearchParams>;
}

export default async function KarInventoryPage({ searchParams }: KarInventoryPageProps) {
  const params = readKarQrParams(await searchParams);

  return (
    <KarQrShell karNumber={params.cart_number} backHref={`/kar${karQrQuery(params)}`} width="wide">
      <KarInventoryFlow karNumber={params.cart_number ?? null} />
    </KarQrShell>
  );
}
