"use client";

// A kar's contents versus this season's needs: per product its bin, how
// many are needed, in the kar, still missing (orange, red when the free
// stock can't cover it) or extra, and how many are free in the warehouse.
// Shared by the kar detail screen and the Kar laden booking screen, so both
// show exactly the same lines. Follows the list-screen table pattern
// (pinned header, capped scroll box).

import { useTranslations } from "next-intl";
import type { StockMasterKarDetail } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface KarContentsTableProps {
  detail: StockMasterKarDetail;
  /** Tailwind max-height of the scroll box (the kar screen has more room than Kar laden). */
  maxHeightClassName?: string;
}

export function KarContentsTable({ detail, maxHeightClassName = "[&>div]:max-h-[65vh]" }: KarContentsTableProps) {
  const t = useTranslations("stockMaster");
  const kar = detail.kar;

  return (
    <div className="flex flex-col gap-2">
      {/* Title, with "Geladen: 13 / 16" when the kar has needs this season. */}
      <h2 className="text-lg font-semibold">
        {t("kars.contentsTitle")}
        {kar.required_total > 0 && (
          <span className="ml-3 text-sm font-normal text-muted-foreground">
            {t("kars.loaded")}: {kar.loaded_toward_required} / {kar.required_total}
          </span>
        )}
      </h2>
      {detail.lines.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t("kars.emptyKar")}</p>
      ) : (
        <div className={cn("rounded-md border [&>div]:overflow-y-auto", maxHeightClassName)}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.product")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background font-bold underline">{t("common.bin")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.needed")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.inKar")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.missing")}</TableHead>
                <TableHead className="sticky top-0 z-20 bg-background text-right font-bold underline">{t("kars.freeAvailable")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {detail.lines.map((line) => (
                <TableRow key={line.product_id}>
                  <TableCell className="font-medium">{line.name}</TableCell>
                  <TableCell className="text-muted-foreground">{line.bin_label ?? t("common.noBin")}</TableCell>
                  <TableCell className="text-right tabular-nums">{line.required || ""}</TableCell>
                  <TableCell className="text-right tabular-nums">{line.in_kar}</TableCell>
                  <TableCell
                    className={cn(
                      "text-right font-semibold tabular-nums",
                      line.missing > 0 &&
                        (line.missing > line.free_available ? "text-destructive" : "text-orange-700 dark:text-orange-300"),
                    )}
                  >
                    {line.missing > 0 ? line.missing : line.surplus > 0 ? t("kars.surplus", { count: line.surplus }) : ""}
                  </TableCell>
                  <TableCell className="text-right tabular-nums text-muted-foreground">{line.free_available}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
