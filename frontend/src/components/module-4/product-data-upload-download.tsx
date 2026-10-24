"use client";

// StockMaster's "Masterdata > Data Upload/Download" screen: a tile grid, one
// tile per table — the products and their four lookup lists (moved here
// from MasterData) — each a shared DataTopicTile
// (components/shared/data-topic-tile.tsx) with template download, bulk
// upload and export. A row with an existing "id" (the export's first
// column) updates that record, a row without one creates a new one.

import { Gauge, Layers, Package, Tag, Warehouse as WarehouseIcon, type LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { API_BASE_URL } from "@/lib/config";
import {
  importProductCategories,
  importProductLimits,
  importProductTypes,
  importProducts,
  importWarehouses,
} from "@/lib/api";
import { DataTopicTile, type ImportRowResult } from "@/components/shared/data-topic-tile";

const BASE = `${API_BASE_URL}/api/modules/module-4`;

/** One tile: its translation group, icon, endpoint paths and upload call. */
interface ProductTable {
  table: "products" | "productTypes" | "warehouses" | "productCategories" | "productLimits";
  icon: LucideIcon;
  /** The upload's path; the template is "<importPath>/template". */
  importPath: string;
  /** The export's path, without "/export". */
  exportPath: string;
  upload: (file: File) => Promise<{ results: NamedImportRow[] }>;
}

/** A result row of these five tables: each names its record by "name". */
type NamedImportRow = Omit<ImportRowResult, "key"> & { name: string | null };

const TABLES: ProductTable[] = [
  { table: "products", icon: Package, importPath: "product-import", exportPath: "products", upload: importProducts },
  {
    table: "productTypes",
    icon: Tag,
    importPath: "product-type-import",
    exportPath: "product-types",
    upload: importProductTypes,
  },
  {
    table: "warehouses",
    icon: WarehouseIcon,
    importPath: "warehouse-import",
    exportPath: "warehouses",
    upload: importWarehouses,
  },
  {
    table: "productCategories",
    icon: Layers,
    importPath: "product-category-import",
    exportPath: "product-categories",
    upload: importProductCategories,
  },
  {
    table: "productLimits",
    icon: Gauge,
    importPath: "product-limit-import",
    exportPath: "product-limits",
    upload: importProductLimits,
  },
];

interface ProductDataUploadDownloadProps {
  /** Whether the user has "create" (not just "view") on the
   * "stockmaster.dataupload" screen: view is enough for the template and
   * export links, the upload control itself needs create.
   */
  canUpload: boolean;
}

export function ProductDataUploadDownload({ canUpload }: ProductDataUploadDownloadProps) {
  const t = useTranslations("stockMaster.dataUploadDownload");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="grid max-w-4xl grid-cols-3 gap-4">
        {TABLES.map((table) => (
          <ProductTableTile key={table.table} canUpload={canUpload} {...table} />
        ))}
      </div>
    </div>
  );
}

/** One table's tile, with its translated texts. */
function ProductTableTile({ canUpload, table, icon, importPath, exportPath, upload }: ProductTable & { canUpload: boolean }) {
  const t = useTranslations("stockMaster.dataUploadDownload");
  const tTable = useTranslations(`stockMaster.dataUploadDownload.${table}`);

  return (
    <DataTopicTile
      moduleKey="module-4"
      icon={icon}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${BASE}/${importPath}/template`}
      exportUrl={`${BASE}/${exportPath}/export`}
      downloadTemplateLabel={t("downloadTemplateLabel")}
      downloadTemplateButton={t("downloadTemplateButton")}
      canUpload={canUpload}
      uploadNotAllowed={t("uploadNotAllowed")}
      chooseFileLabel={t("chooseFileLabel")}
      uploadButton={t("uploadButton")}
      importFailed={t("importFailed")}
      importSummary={(counts) => t("importSummary", counts)}
      hint={t("idHint")}
      importColumnRow={t("importColumnRow")}
      importColumnKey={tTable("importColumnKey")}
      importColumnOutcome={t("importColumnOutcome")}
      importColumnDetail={t("importColumnDetail")}
      importOutcomeLabel={(outcome) => t(`importOutcome.${outcome}`)}
      exportLabel={t("exportLabel")}
      exportButton={tTable("exportButton")}
      onUpload={async (file) => (await upload(file)).results.map((row) => ({ ...row, key: row.name }))}
    />
  );
}
