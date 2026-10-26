"use client";

// The festival dropdown of Atelier's Reservaties and Voorbereiden screens:
// the chosen season's active festivals (loaded here), the choice kept in the
// "?festival=" URL parameter so it travels between the two screens. Without
// a choice it starts on the first festival that hasn't ended yet (else the
// first one).

import { useTranslations } from "next-intl";
import { useSearchParams } from "next/navigation";
import { usePathname, useRouter } from "@/i18n/navigation";
import { listAtelierFestivals } from "@/lib/api";
import { formatDate, formatDateNl } from "@/lib/date-time";
import type { AtelierFestival } from "@/lib/types";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useKeyedLoad } from "@/components/module-4/use-keyed-load";

/** The season's festivals and the chosen one (null while loading or none). */
export function useAtelierFestival(seasonId: number | null) {
  const searchParams = useSearchParams();
  const festivals = useKeyedLoad<AtelierFestival[]>(seasonId === null ? null : String(seasonId), () =>
    listAtelierFestivals(seasonId!),
  );
  const list = festivals.data ?? [];

  const fromUrl = Number(searchParams.get("festival"));
  // Today's date in Belgian time, to skip festivals that are over.
  const today = formatDate(new Date().toISOString());
  const festival =
    list.find((item) => item.id === fromUrl) ?? list.find((item) => item.end_date >= today) ?? list[0] ?? null;
  return { festivals: list, festival, isLoading: festivals.isLoading };
}

interface AtelierFestivalSelectProps {
  festivals: AtelierFestival[];
  festival: AtelierFestival | null;
}

export function AtelierFestivalSelect({ festivals, festival }: AtelierFestivalSelectProps) {
  const t = useTranslations("atelier.common");
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Store the choice in the URL, keeping the other parameters (e.g. ?season=).
  function handleChange(value: string | null) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set("festival", value);
    router.replace(`${pathname}?${params.toString()}`);
  }

  function festivalLabel(item: AtelierFestival) {
    const period =
      item.start_date === item.end_date
        ? formatDateNl(item.start_date)
        : `${formatDateNl(item.start_date)} – ${formatDateNl(item.end_date)}`;
    return `${item.name} (${period})`;
  }

  return (
    // At least w-80, but as wide as the label of a festival with a date range
    // (never shrunk by the row around it: the row wraps instead), so it never
    // runs over the fields next to it. The trigger fills the column.
    <div className="flex max-w-full min-w-80 shrink-0 flex-col gap-2">
      <Label htmlFor="atelier-festival">{t("festivalLabel")}</Label>
      <Select value={festival ? String(festival.id) : ""} onValueChange={handleChange}>
        <SelectTrigger id="atelier-festival" className="w-full" title={festival ? festivalLabel(festival) : undefined}>
          <SelectValue>
            {(value: string | null) => {
              const item = festivals.find((candidate) => String(candidate.id) === value);
              return item ? festivalLabel(item) : t("noFestival");
            }}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {festivals.map((item) => (
            <SelectItem key={item.id} value={String(item.id)}>
              {festivalLabel(item)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
