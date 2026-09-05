// MasterData's "Delivery Method" screen (nested under "Teams") — see
// DeliveryMethodManagement for the actual UI.

import { getTranslations } from "next-intl/server";
import { ServerApiError, serverApiFetch } from "@/lib/server-api";
import type { DeliveryMethod } from "@/lib/types";
import { DeliveryMethodManagement } from "@/components/module-9/delivery-method-management";

export default async function MasterDataDeliveryMethodPage() {
  const tErrors = await getTranslations("errors");

  let deliveryMethods: DeliveryMethod[] | null = null;
  try {
    deliveryMethods = await serverApiFetch<DeliveryMethod[]>("/api/modules/module-9/delivery-methods");
  } catch (error) {
    if (error instanceof ServerApiError && error.status === 403) {
      return <p className="text-sm text-destructive">{tErrors("forbidden")}</p>;
    }
    throw error;
  }

  return <DeliveryMethodManagement initialDeliveryMethods={deliveryMethods} />;
}
