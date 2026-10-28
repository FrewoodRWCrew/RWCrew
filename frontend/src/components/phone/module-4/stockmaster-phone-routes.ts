// The addresses of StockMaster's phone screens, in one place so screens link
// to each other without spelling out URLs.

import { phoneModuleHref } from "@/components/phone/shared/phone-modules";

const BASE_HREF = phoneModuleHref("module-4");

export const stockMasterPhoneRoutes = {
  menu: BASE_HREF,
  /** Count a kar by voice: scan, Ophalen/Terugbrengen, speak, save. */
  voiceCount: `${BASE_HREF}/voice-count`,
};
