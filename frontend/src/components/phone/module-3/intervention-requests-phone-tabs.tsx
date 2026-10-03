"use client";

// The module's bottom tab bar: "Akties" (the requests, only with the right
// to see them) and "KPI overzicht".

import { BarChart3, Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { interventionRequestsPhoneRoutes } from "@/components/phone/module-3/intervention-requests-phone-routes";
import { PhoneBottomTabs, type PhoneTab } from "@/components/phone/shared/phone-bottom-tabs";

export function InterventionRequestsPhoneTabs({ showRequestsTab }: { showRequestsTab: boolean }) {
  const t = useTranslations("interventionRequests.phone");

  const tabs: PhoneTab[] = [
    ...(showRequestsTab ? [{ href: interventionRequestsPhoneRoutes.requests, label: t("actionsTab"), icon: Zap }] : []),
    { href: interventionRequestsPhoneRoutes.kpi, label: t("kpiTab"), icon: BarChart3 },
  ];

  return <PhoneBottomTabs tabs={tabs} activeClassName="text-orange-600 dark:text-orange-400" />;
}
