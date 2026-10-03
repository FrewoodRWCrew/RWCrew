// The addresses of Interventie Aanvragen's phone screens, in one place so
// screens link to each other without spelling out URLs.

import { phoneModuleHref } from "@/components/phone/shared/phone-modules";

const BASE_HREF = phoneModuleHref("module-3");

export const interventionRequestsPhoneRoutes = {
  /** The "Akties" tab: the list of requests (the module's start page). */
  requests: BASE_HREF,
  kpi: `${BASE_HREF}/kpi`,
  newRequest: `${BASE_HREF}/request/new`,
  request: (requestId: number) => `${BASE_HREF}/request/${requestId}`,
};
