// This is Module 7's own page file. Right now it just renders the
// shared "coming soon" placeholder (see ModulePlaceholderPage) for its
// own module key. Once Module 7's real functionality is designed,
// this file is where its actual page content gets built, keeping
// everything about Module 7's frontend together in this folder.

import { ModulePlaceholderPage } from "@/components/shared/module-placeholder-page";

export default function ModulePage() {
  return <ModulePlaceholderPage moduleKey="module-7" />;
}
