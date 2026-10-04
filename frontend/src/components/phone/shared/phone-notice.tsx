// A short message in a dashed box: "no access", "nothing found", and so on.

import type { ReactNode } from "react";

export function PhoneNotice({ children }: { children: ReactNode }) {
  return <p className="rounded-xl border border-dashed p-4 text-center text-sm text-muted-foreground">{children}</p>;
}
