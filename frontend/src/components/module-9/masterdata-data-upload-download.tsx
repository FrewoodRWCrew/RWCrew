"use client";

// MasterData's "Data Upload/Download" screen: a tile grid, one tile per
// master-data table's bulk import/export tools, each a shared DataTopicTile
// (components/shared/data-topic-tile.tsx). The products and their lookup
// lists have their own grid in StockMaster
// (components/module-4/product-data-upload-download.tsx).
//
// Each tile's dialog combines template download / bulk upload / export.
// A row with an existing "id" (the export's first column) updates that
// record, a row without one creates a new one (see module_9/xlsx_common.py
// on the backend). Team's tile covers the team's own fields; its links
// (tasks, Kernleden, festivals, Ploegverantwoordelijken) have tiles of their
// own, where an upload only adds links ("unchanged" when one already exists).

import {
  CalendarRange,
  ClipboardList,
  ContactRound,
  ListChecks,
  MapPin,
  PartyPopper,
  Ticket,
  Truck,
  UserCheck,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { API_BASE_URL } from "@/lib/config";
import {
  importDeliveryMethods,
  importFestivals,
  importSeasons,
  importTeamLinks,
  importTeamLocations,
  importTeamTasks,
  importTeams,
  type TeamLinkImportPath,
} from "@/lib/api";
import { DataTopicTile } from "@/components/shared/data-topic-tile";

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
      moduleKey="module-9"
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

function FestivalDataTile({ canUpload }: { canUpload: boolean }) {
  const t = useTranslations("masterdata.dataUploadDownload");
  const tTable = useTranslations("masterdata.dataUploadDownload.festival");

  return (
    <DataTopicTile
      moduleKey="module-9"
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
      moduleKey="module-9"
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
      moduleKey="module-9"
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
      moduleKey="module-9"
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
      moduleKey="module-9"
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
      moduleKey="module-9"
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
