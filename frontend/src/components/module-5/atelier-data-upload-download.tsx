"use client";

// Atelier's "Masterdata > Data Upload/Download" screen: one shared
// DataTopicTile (components/shared/data-topic-tile.tsx) per table — Maten,
// Artikelen, Artikelmaten, Reservaties and Pakketlijnen — each with template download,
// bulk upload and export. Maten/Artikelen use the "id" column (existing id =
// update, empty = new); Artikelmaten, Reservaties and Pakketlijnen are matched on their
// natural key (see backend/app/modules/module_5/xlsx_imports.py).

import { CalendarCheck, Package, Ruler, Shirt, Tags, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { API_BASE_URL } from "@/lib/config";
import { importAtelierXlsx } from "@/lib/api";
import { DataTopicTile } from "@/components/shared/data-topic-tile";

const BASE = `${API_BASE_URL}/api/modules/module-5`;

/** One tile: its translation group, icon and the backend's URL part. */
interface AtelierTable {
  table: "sizes" | "articles" | "articleSizes" | "reservations" | "packageLines";
  icon: LucideIcon;
  /** "/<path>-import", "/<path>-import/template" and "/<path>/export". */
  path: string;
}

const TABLES: AtelierTable[] = [
  { table: "sizes", icon: Ruler, path: "sizes" },
  { table: "articles", icon: Shirt, path: "articles" },
  { table: "articleSizes", icon: Tags, path: "article-sizes" },
  { table: "reservations", icon: CalendarCheck, path: "reservations" },
  { table: "packageLines", icon: Package, path: "package-lines" },
];

interface AtelierDataUploadDownloadProps {
  /** "create" on atelier.dataupload: view is enough for templates and
   * exports, the upload itself needs create. */
  canUpload: boolean;
}

export function AtelierDataUploadDownload({ canUpload }: AtelierDataUploadDownloadProps) {
  const t = useTranslations("atelier.dataUploadDownload");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="grid max-w-4xl grid-cols-2 gap-4 lg:grid-cols-4">
        {TABLES.map((table) => (
          <AtelierTableTile key={table.table} canUpload={canUpload} {...table} />
        ))}
      </div>
    </div>
  );
}

/** One table's tile, with its translated texts. */
function AtelierTableTile({ canUpload, table, icon, path }: AtelierTable & { canUpload: boolean }) {
  const t = useTranslations("atelier.dataUploadDownload");
  const tTable = useTranslations(`atelier.dataUploadDownload.${table}`);

  return (
    <DataTopicTile
      moduleKey="module-5"
      icon={icon}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${BASE}/${path}-import/template`}
      exportUrl={`${BASE}/${path}/export`}
      downloadTemplateLabel={t("downloadTemplateLabel")}
      downloadTemplateButton={t("downloadTemplateButton")}
      canUpload={canUpload}
      uploadNotAllowed={t("uploadNotAllowed")}
      chooseFileLabel={t("chooseFileLabel")}
      uploadButton={t("uploadButton")}
      importFailed={t("importFailed")}
      importSummary={(counts) => t("importSummary", counts)}
      hint={tTable("hint")}
      importColumnRow={t("importColumnRow")}
      importColumnKey={tTable("importColumnKey")}
      importColumnOutcome={t("importColumnOutcome")}
      importColumnDetail={t("importColumnDetail")}
      importOutcomeLabel={(outcome) => t(`importOutcome.${outcome}`)}
      exportLabel={t("exportLabel")}
      exportButton={tTable("exportButton")}
      onUpload={async (file) => (await importAtelierXlsx(path, file)).results.map((row) => ({ ...row, key: row.name }))}
    />
  );
}
