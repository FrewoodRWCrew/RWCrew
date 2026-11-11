"use client";

// Kar inventaris (public, no login): the lock code first (kar-code-entry.tsx),
// then the counting screen (kar-inventory-screen.tsx). The token of an
// unlocked kar is kept for this tab (kar-inventory-token.ts); when the backend
// no longer accepts it (2 h passed, or the lock code changed) the code is
// asked again.

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Loader2, RotateCw } from "lucide-react";

import { ApiError, getKarInventoryContext } from "@/lib/api";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";
import { KarQrCard } from "@/components/shared/kar-qr/kar-qr-shell";
import { KarCodeEntry } from "./kar-code-entry";
import { KarInventoryScreen } from "./kar-inventory-screen";
import { storeKarInventoryToken, useKarInventoryToken } from "./kar-inventory-token";

export function KarInventoryFlow({ karNumber }: { karNumber: string | null }) {
  const t = useTranslations("stockMaster.publicInventory");
  // The kar being counted: the QR code's, or the one typed on the code screen.
  const [kar, setKar] = useState<string | null>(karNumber);
  const [notice, setNotice] = useState<string | null>(null);
  const token = useKarInventoryToken(kar);

  // A refused token: forget it and ask the code again.
  function expire() {
    if (kar) storeKarInventoryToken(kar, null);
    setNotice(t("sessionEnded"));
  }

  const context = useKeyedLoad(token, async () => {
    try {
      return await getKarInventoryContext(token!);
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) expire();
      throw caught;
    }
  });

  if (!token) {
    return (
      <KarCodeEntry
        karNumber={karNumber}
        notice={notice}
        onUnlocked={(unlockedKar, newToken) => {
          setNotice(null);
          setKar(unlockedKar);
          storeKarInventoryToken(unlockedKar, newToken);
        }}
      />
    );
  }

  if (context.failed) {
    return (
      <KarQrCard className="mt-6 flex flex-col items-center gap-4 p-6 text-center">
        <p>{t("errors.network")}</p>
        <button
          type="button"
          onClick={context.reload}
          className="flex h-[52px] items-center gap-2 rounded-[12px] bg-[var(--kq-teal)] px-6 font-semibold text-white"
        >
          <RotateCw className="size-5" />
          {t("retry")}
        </button>
      </KarQrCard>
    );
  }

  if (!context.data) {
    return <Loader2 className="mx-auto mt-16 size-8 animate-spin text-[var(--kq-muted)]" />;
  }

  return <KarInventoryScreen context={context.data} token={token} onSaved={context.reload} onExpired={expire} />;
}
