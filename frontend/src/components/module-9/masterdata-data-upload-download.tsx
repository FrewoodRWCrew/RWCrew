"use client";

// MasterData's "Data Upload/Download" screen: a tile grid, one tile per
// master-data table's bulk import/export tools — direct copy of
// KarTracker's own components/module-2/kar-data-upload-download.tsx
// (same DataTopicTile presentational component, duplicated here rather
// than shared, matching the convention that each module's UI stays
// self-contained under its own components/module-{N}/ folder).
//
// Each tile's dialog combines template download / bulk upload / export.
// A row with an existing "id" (the export's first column) updates that
// record, a row without one creates a new one (see module_9/xlsx_common.py
// on the backend). Team's tile covers the team's own fields; its links
// (tasks, Kernleden, festivals, Ploegverantwoordelijken) have tiles of their
// own, where an upload only adds links ("unchanged" when one already exists).

import { useState } from "react";
import {
  CalendarRange,
  Gauge,
  Layers,
  ClipboardList,
  ContactRound,
  ListChecks,
  MapPin,
  Package,
  PartyPopper,
  Tag,
  Ticket,
  Truck,
  UserCheck,
  Users,
  Warehouse as WarehouseIcon,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { API_BASE_URL } from "@/lib/config";
import {
  ApiError,
  importDeliveryMethods,
  importFestivals,
  importProductCategories,
  importProductLimits,
  importProductTypes,
  importProducts,
  importSeasons,
  importTeamLinks,
  importTeamLocations,
  importTeamTasks,
  importTeams,
  importWarehouses,
  type TeamLinkImportPath,
} from "@/lib/api";
import type { MasterDataImportOutcome } from "@/lib/types";
import { getModuleTheme } from "@/lib/module-theme";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/** One row's outcome, normalized to a common shape regardless of which
 * table's own wire type it came from — each tile wrapper below maps its
 * own "key" field (name/location/delivery_method/team_tasks) into this
 * before handing it to the shared dialog.
 */
interface ImportRowResult {
  row_number: number;
  key: string | null;
  outcome: MasterDataImportOutcome;
  detail: string | null;
}

/** How many rows of an upload ended in each outcome (the summary line). */
type ImportCounts = Record<"created" | "updated" | "unchanged" | "errors", number>;

const OUTCOME_BADGE_VARIANT: Record<
  MasterDataImportOutcome,
  "default" | "secondary" | "outline" | "destructive"
> = {
  created: "default",
  updated: "secondary",
  unchanged: "outline",
  error: "destructive",
};

interface MasterDataDataUploadDownloadProps {
  /** Whether the current user has "create" (not just "view") permission on
   * the "masterdata.dataupload" screen — gates the upload control on every
   * tile below, since view-only access is enough to reach this screen and
   * use its template/export links, but not enough to actually import.
   */
  canUpload: boolean;
}

export function MasterDataDataUploadDownload({ canUpload }: MasterDataDataUploadDownloadProps) {
  const t = useTranslations("masterdata.dataUploadDownload");

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight underline">{t("title")}</h1>
        <p className="text-muted-foreground">{t("description")}</p>
      </div>

      <div className="grid max-w-4xl grid-cols-3 gap-4">
        <SeasonDataTile canUpload={canUpload} />
        <ProductDataTile canUpload={canUpload} />
        <ProductTypeDataTile canUpload={canUpload} />
        <WarehouseDataTile canUpload={canUpload} />
        <ProductCategoryDataTile canUpload={canUpload} />
        <ProductLimitDataTile canUpload={canUpload} />
        <FestivalDataTile canUpload={canUpload} />
        <TeamDataTile canUpload={canUpload} />
        <TeamLocationDataTile canUpload={canUpload} />
        <DeliveryMethodDataTile canUpload={canUpload} />
        <TeamTaskDataTile canUpload={canUpload} />
        <TeamLinkDataTile
          canUpload={canUpload}
          icon={ClipboardList}
          table="teamTaskLinks"
          path="team-task-link-import"
          exportPath="team-task-links"
        />
        <TeamLinkDataTile
          canUpload={canUpload}
          icon={UserCheck}
          table="teamKernleden"
          path="team-kernlid-import"
          exportPath="team-kernleden"
        />
        <TeamLinkDataTile
          canUpload={canUpload}
          icon={Ticket}
          table="teamFestivals"
          path="team-festival-import"
          exportPath="team-festivals"
        />
        <TeamLinkDataTile
          canUpload={canUpload}
          icon={ContactRound}
          table="teamResponsibles"
          path="team-responsible-import"
          exportPath="team-responsibles"
        />
      </div>
    </div>
  );
}

function SeasonDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.season");

  return (
    <DataTopicTile
      icon={CalendarRange}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/season-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/seasons/export`}
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
      onUpload={async (file) => {
        const response = await importSeasons(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function ProductDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.products");

  return (
    <DataTopicTile
      icon={Package}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/product-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/products/export`}
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
      onUpload={async (file) => {
        const response = await importProducts(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function ProductTypeDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.productTypes");

  return (
    <DataTopicTile
      icon={Tag}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/product-type-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/product-types/export`}
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
      onUpload={async (file) => {
        const response = await importProductTypes(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function WarehouseDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.warehouses");

  return (
    <DataTopicTile
      icon={WarehouseIcon}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/warehouse-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/warehouses/export`}
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
      onUpload={async (file) => {
        const response = await importWarehouses(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function ProductCategoryDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.productCategories");

  return (
    <DataTopicTile
      icon={Layers}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/product-category-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/product-categories/export`}
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
      onUpload={async (file) => {
        const response = await importProductCategories(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function ProductLimitDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.productLimits");

  return (
    <DataTopicTile
      icon={Gauge}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/product-limit-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/product-limits/export`}
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
      onUpload={async (file) => {
        const response = await importProductLimits(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function FestivalDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.festival");

  return (
    <DataTopicTile
      icon={PartyPopper}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/festival-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/festivals/export`}
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
      onUpload={async (file) => {
        const response = await importFestivals(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function TeamDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.teams");

  return (
    <DataTopicTile
      icon={Users}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/team-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/teams/export`}
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
      onUpload={async (file) => {
        const response = await importTeams(file);
        return response.results.map((row) => ({ ...row, key: row.name }));
      }}
    />
  );
}

function TeamLocationDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.teamLocation");

  return (
    <DataTopicTile
      icon={MapPin}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/team-location-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/team-locations/export`}
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
      onUpload={async (file) => {
        const response = await importTeamLocations(file);
        return response.results.map((row) => ({ ...row, key: row.location }));
      }}
    />
  );
}

function DeliveryMethodDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.deliveryMethod");

  return (
    <DataTopicTile
      icon={Truck}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/delivery-method-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/delivery-methods/export`}
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
      onUpload={async (file) => {
        const response = await importDeliveryMethods(file);
        return response.results.map((row) => ({ ...row, key: row.delivery_method }));
      }}
    />
  );
}

function TeamTaskDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.teamTasks");

  return (
    <DataTopicTile
      icon={ListChecks}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/team-task-import/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/team-tasks/export`}
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
      onUpload={async (file) => {
        const response = await importTeamTasks(file);
        return response.results.map((row) => ({ ...row, key: row.team_tasks }));
      }}
    />
  );
}

interface TeamLinkDataTileProps {
  canUpload: boolean;
  icon: LucideIcon;
  /** The tile's translation group under masterdata.dataUploadDownload. */
  table: "teamTaskLinks" | "teamKernleden" | "teamFestivals" | "teamResponsibles";
  /** The upload's path; the template is "<path>/template". */
  path: TeamLinkImportPath;
  /** The export's path, without "/export". */
  exportPath: string;
}

/**
 * The tiles of the team links (tasks, Kernleden and festivals per team) and
 * the Ploegverantwoordelijken: they share one response shape, so one
 * component serves all four.
 */
function TeamLinkDataTile({ canUpload, icon, table, path, exportPath }: TeamLinkDataTileProps) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations(`masterdata.dataUploadDownload.${table}`);

  return (
    <DataTopicTile
      icon={icon}
      tileTitle={tTable("tileTitle")}
      dialogTitle={tTable("tileTitle")}
      dialogDescription={tTable("dialogDescription")}
      templateUrl={`${API_BASE_URL}/api/modules/module-9/${path}/template`}
      exportUrl={`${API_BASE_URL}/api/modules/module-9/${exportPath}/export`}
      downloadTemplateLabel={t("downloadTemplateLabel")}
      downloadTemplateButton={t("downloadTemplateButton")}
      canUpload={canUpload}
      uploadNotAllowed={t("uploadNotAllowed")}
      chooseFileLabel={t("chooseFileLabel")}
      uploadButton={t("uploadButton")}
      importFailed={t("importFailed")}
      importSummary={(counts) => t("importSummary", counts)}
      // The Ploegverantwoordelijken are records with an id; the others only add links.
      hint={table === "teamResponsibles" ? t("idHint") : t("linkHint")}
      importColumnRow={t("importColumnRow")}
      importColumnKey={tTable("importColumnKey")}
      importColumnOutcome={t("importColumnOutcome")}
      importColumnDetail={t("importColumnDetail")}
      importOutcomeLabel={(outcome) => t(`importOutcome.${outcome}`)}
      exportLabel={t("exportLabel")}
      exportButton={tTable("exportButton")}
      onUpload={async (file) => (await importTeamLinks(path, file)).results}
    />
  );
}

interface DataTopicTileProps {
  icon: LucideIcon;
  tileTitle: string;
  dialogTitle: string;
  dialogDescription: string;
  /** How the upload treats existing records (shown under the description). */
  hint: string;
  templateUrl: string;
  exportUrl: string;
  downloadTemplateLabel: string;
  downloadTemplateButton: string;
  /** Whether the current user has "create" permission — hides the file
   * input/upload button (in favour of an explanatory note) when false. */
  canUpload: boolean;
  uploadNotAllowed: string;
  chooseFileLabel: string;
  uploadButton: string;
  importFailed: string;
  importSummary: (counts: ImportCounts) => string;
  importColumnRow: string;
  importColumnKey: string;
  importColumnOutcome: string;
  importColumnDetail: string;
  importOutcomeLabel: (outcome: ImportRowResult["outcome"]) => string;
  exportLabel: string;
  exportButton: string;
  onUpload: (file: File) => Promise<ImportRowResult[]>;
}

/**
 * One tile on the Data Upload/Download grid: a button styled as an
 * outlined card (this module's own accent colour as the border, not a
 * solid fill) that opens a dialog with that table's template download /
 * bulk upload / export tools. Direct copy of KarTracker's own
 * DataTopicTile (components/module-2/kar-data-upload-download.tsx).
 */
function DataTopicTile({
  icon: Icon,
  tileTitle,
  dialogTitle,
  dialogDescription,
  hint,
  templateUrl,
  exportUrl,
  downloadTemplateLabel,
  downloadTemplateButton,
  canUpload,
  uploadNotAllowed,
  chooseFileLabel,
  uploadButton,
  importFailed,
  importSummary,
  importColumnRow,
  importColumnKey,
  importColumnOutcome,
  importColumnDetail,
  importOutcomeLabel,
  exportLabel,
  exportButton,
  onUpload,
}: DataTopicTileProps) {
  const { accentColorToken } = getModuleTheme("module-9");
  const accentColor = `var(--color-${accentColorToken})`;

  const [isOpen, setIsOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [results, setResults] = useState<ImportRowResult[] | null>(null);

  function handleOpenChange(open: boolean) {
    setIsOpen(open);
    if (open) {
      // Start from a clean slate each time the dialog is opened, so a
      // previous import's results don't linger behind a new file pick.
      setFile(null);
      setResults(null);
    }
  }

  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    // Picking a different file always clears any displayed results — they
    // describe the previous file's outcome, not this one, so leaving them
    // up would make it look like they belong to the newly picked file.
    setFile(event.target.files?.[0] ?? null);
    setResults(null);
  }

  async function handleUpload() {
    if (!file) return;

    // Clear out the previous upload's results immediately, so a slow or
    // failed request never leaves stale success/error rows on screen
    // looking like they belong to the file just picked.
    setResults(null);
    setIsUploading(true);
    try {
      setResults(await onUpload(file));
    } catch (error) {
      const message = error instanceof ApiError ? error.message : importFailed;
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  // Counts per outcome, for the summary line above the results table.
  const countOf = (outcome: MasterDataImportOutcome) => results?.filter((row) => row.outcome === outcome).length ?? 0;
  const counts: ImportCounts = {
    created: countOf("created"),
    updated: countOf("updated"),
    unchanged: countOf("unchanged"),
    errors: countOf("error"),
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger
        render={
          <button type="button" className="block text-left">
            <div
              className="relative flex h-36 flex-col rounded-xl border-2 bg-card p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"
              style={{ borderColor: accentColor }}
            >
              <div className="flex flex-1 items-center justify-center" style={{ color: accentColor }}>
                <Icon className="size-16" aria-hidden="true" />
              </div>
              <span className="text-center text-sm font-semibold">{tileTitle}</span>
            </div>
          </button>
        }
      />
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{dialogTitle}</DialogTitle>
          <DialogDescription>{dialogDescription}</DialogDescription>
        </DialogHeader>

        <p className="rounded-md bg-muted/50 px-3 py-2 text-sm text-muted-foreground">{hint}</p>

        <div className="flex flex-col gap-2">
          <Label>{downloadTemplateLabel}</Label>
          <a href={templateUrl}>
            <Button variant="outline" type="button">
              {downloadTemplateButton}
            </Button>
          </a>
        </div>

        {canUpload ? (
          <div className="flex flex-col gap-2">
            <Label htmlFor="data-topic-import-file">{chooseFileLabel}</Label>
            <Input
              id="data-topic-import-file"
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              onChange={handleFileChange}
            />
            <Button onClick={handleUpload} disabled={isUploading || !file} className="self-start">
              {uploadButton}
            </Button>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">{uploadNotAllowed}</p>
        )}

        {results && (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-muted-foreground">{importSummary(counts)}</p>
            <div className="rounded-md border [&>div]:max-h-72 [&>div]:overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {importColumnRow}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {importColumnKey}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {importColumnOutcome}
                    </TableHead>
                    <TableHead className="sticky top-0 z-20 bg-background font-bold underline">
                      {importColumnDetail}
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {results.map((row) => (
                    <TableRow key={row.row_number}>
                      <TableCell>{row.row_number}</TableCell>
                      <TableCell className="font-medium">{row.key}</TableCell>
                      <TableCell>
                        <Badge variant={OUTCOME_BADGE_VARIANT[row.outcome]}>{importOutcomeLabel(row.outcome)}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{row.detail}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        <DialogFooter className="justify-start sm:justify-start">
          <div className="flex flex-col gap-2">
            <Label>{exportLabel}</Label>
            <a href={exportUrl}>
              <Button variant="outline" type="button">
                {exportButton}
              </Button>
            </a>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
