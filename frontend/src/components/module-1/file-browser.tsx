"use client";

// TagScan's "Dashboard" screen: an Explorer-style browser over the folder
// where incoming CSV scan files currently land. Three panes:
//   1. Folder tree (left) — the whole folder structure.
//   2. File list (middle) — files directly inside whichever folder is
//      selected in the tree.
//   3. Content preview (right) — a "notepad"-style read-only view of
//      whichever file is selected in the file list.
// Users with "delete" on this screen can check files in the file list and
// delete them from the server (the Files pane's bin button).

import { useCallback, useState } from "react";
import { ChevronDown, ChevronRight, File, Folder, RefreshCw, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import {
  ApiError,
  deleteTagscanFiles,
  getTagscanFileContent,
  getTagscanFolderTree,
  listTagscanFiles,
} from "@/lib/api";
import type { TagscanFileContent, TagscanFileEntry, TagscanFolderNode } from "@/lib/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

interface FileBrowserProps {
  initialTree: TagscanFolderNode;
  // The folder selected on open, whose files are initialFiles.
  initialFolderPath: string;
  initialFiles: TagscanFileEntry[];
  /** Whether the user has "delete" on this screen (shows the checkboxes + bin button). */
  canDelete: boolean;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileBrowser({ initialTree, initialFolderPath, initialFiles, canDelete }: FileBrowserProps) {
  const t = useTranslations("tagscan.dashboard");

  const [tree, setTree] = useState(initialTree);
  const [selectedFolderPath, setSelectedFolderPath] = useState<string>(initialFolderPath);
  const [files, setFiles] = useState<TagscanFileEntry[]>(initialFiles);
  const [filesError, setFilesError] = useState<string | null>(null);

  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<TagscanFileContent | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  // The files checked for deletion — always within the folder shown.
  const [checkedPaths, setCheckedPaths] = useState<Set<string>>(new Set());

  const loadFiles = useCallback(
    async (folderPath: string) => {
      setFilesError(null);
      // A new listing starts with nothing checked.
      setCheckedPaths(new Set());
      try {
        const entries = await listTagscanFiles(folderPath);
        setFiles(entries);
      } catch (error) {
        setFiles([]);
        setFilesError(error instanceof ApiError ? error.message : t("loadFilesFailed"));
      }
    },
    [t],
  );

  async function handleSelectFolder(folderPath: string) {
    setSelectedFolderPath(folderPath);
    setSelectedFilePath(null);
    setFileContent(null);
    await loadFiles(folderPath);
  }

  async function handleSelectFile(filePath: string) {
    setSelectedFilePath(filePath);
    setFileContent(null);
    setContentError(null);
    setIsLoadingContent(true);
    try {
      const content = await getTagscanFileContent(filePath);
      setFileContent(content);
    } catch (error) {
      setContentError(error instanceof ApiError ? error.message : t("loadContentFailed"));
    } finally {
      setIsLoadingContent(false);
    }
  }

  const allChecked = files.length > 0 && files.every((file) => checkedPaths.has(file.path));
  const someChecked = files.some((file) => checkedPaths.has(file.path));

  function toggleCheckAll(checked: boolean) {
    setCheckedPaths(checked ? new Set(files.map((file) => file.path)) : new Set());
  }

  function toggleCheckOne(filePath: string, checked: boolean) {
    setCheckedPaths((current) => {
      const next = new Set(current);
      if (checked) next.add(filePath);
      else next.delete(filePath);
      return next;
    });
  }

  // After a delete: drop the preview if its file is gone, then reload the
  // tree and the folder's files (which also clears the checkboxes).
  async function handleDeleted(deletedPaths: string[]) {
    if (selectedFilePath && deletedPaths.includes(selectedFilePath)) {
      setSelectedFilePath(null);
      setFileContent(null);
    }
    await handleRefresh();
  }

  async function handleRefresh() {
    try {
      const freshTree = await getTagscanFolderTree();
      setTree(freshTree);
      await loadFiles(selectedFolderPath);
    } catch {
      setFilesError(t("loadTreeFailed"));
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">{t("title")}</h1>
        <Button variant="outline" size="sm" onClick={handleRefresh}>
          <RefreshCw className="size-4" />
          {t("refresh")}
        </Button>
      </div>

      <div className="grid h-[calc(100vh-13rem)] grid-cols-[minmax(180px,1fr)_minmax(220px,1.2fr)_2fr] gap-4">
        <div className="flex flex-col overflow-hidden rounded-md border">
          <div className="border-b bg-muted/50 px-3 py-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            {t("foldersHeading")}
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            <FolderTreeNode
              node={tree}
              depth={0}
              selectedPath={selectedFolderPath}
              onSelect={handleSelectFolder}
            />
          </div>
        </div>

        <div className="flex flex-col overflow-hidden rounded-md border">
          <div className="flex items-center justify-between gap-2 border-b bg-muted/50 px-3 py-1">
            <span className="py-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {t("filesHeading")}
            </span>
            {canDelete && <DeleteFilesAlertDialog paths={[...checkedPaths]} onDeleted={handleDeleted} />}
          </div>
          <div className="flex-1 overflow-y-auto">
            {filesError && <p className="p-3 text-sm text-destructive">{filesError}</p>}
            {!filesError && files.length === 0 && (
              <p className="p-3 text-sm text-muted-foreground">{t("emptyFolder")}</p>
            )}
            {!filesError && files.length > 0 && (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    {canDelete && (
                      <th className="w-8 py-1.5 pl-3">
                        <Checkbox
                          checked={allChecked}
                          indeterminate={someChecked && !allChecked}
                          onCheckedChange={(checked) => toggleCheckAll(checked === true)}
                          aria-label={t("selectAll")}
                        />
                      </th>
                    )}
                    <th className="px-3 py-1.5 font-medium">{t("columnName")}</th>
                    <th className="px-3 py-1.5 font-medium">{t("columnSize")}</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((file) => (
                    <tr
                      key={file.path}
                      onClick={() => handleSelectFile(file.path)}
                      className={cn(
                        "cursor-pointer border-b last:border-0 hover:bg-accent",
                        selectedFilePath === file.path && "bg-accent",
                      )}
                    >
                      {canDelete && (
                        // Checking a file must not also open its preview.
                        <td className="w-8 py-1.5 pl-3" onClick={(event) => event.stopPropagation()}>
                          <Checkbox
                            checked={checkedPaths.has(file.path)}
                            onCheckedChange={(checked) => toggleCheckOne(file.path, checked === true)}
                            aria-label={t("selectFile", { name: file.name })}
                          />
                        </td>
                      )}
                      <td className="flex items-center gap-2 px-3 py-1.5">
                        <File className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                        {file.name}
                      </td>
                      <td className="px-3 py-1.5 text-muted-foreground">{formatSize(file.size_bytes)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div className="flex flex-col overflow-hidden rounded-md border">
          <div className="border-b bg-muted/50 px-3 py-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            {t("previewHeading")}
          </div>
          <div className="flex-1 overflow-auto p-3">
            {!selectedFilePath && <p className="text-sm text-muted-foreground">{t("selectFilePrompt")}</p>}
            {selectedFilePath && isLoadingContent && <p className="text-sm text-muted-foreground">…</p>}
            {selectedFilePath && contentError && <p className="text-sm text-destructive">{contentError}</p>}
            {fileContent && (
              <>
                {fileContent.truncated && (
                  <p className="mb-2 text-xs text-muted-foreground italic">{t("truncatedNotice")}</p>
                )}
                <pre className="font-mono text-xs whitespace-pre-wrap">{fileContent.content}</pre>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

interface DeleteFilesAlertDialogProps {
  paths: string[];
  onDeleted: (paths: string[]) => void | Promise<void>;
}

/** The Files pane's bin button: deletes every checked file from the server,
 * after a confirmation. Disabled while nothing is checked. */
function DeleteFilesAlertDialog({ paths, onDeleted }: DeleteFilesAlertDialogProps) {
  const t = useTranslations("tagscan.dashboard");
  const tCommon = useTranslations("common");
  const [isOpen, setIsOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleConfirmDelete() {
    setIsDeleting(true);
    try {
      const { deleted } = await deleteTagscanFiles(paths);
      toast.success(t("filesDeleted", { count: deleted }));
      setIsOpen(false);
      await onDeleted(paths);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : t("deleteFailed");
      toast.error(message);
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <AlertDialog open={isOpen} onOpenChange={setIsOpen}>
      <AlertDialogTrigger
        render={
          <Button variant="outline" size="sm" disabled={paths.length === 0}>
            <Trash2 className="size-4 text-destructive" />
            {t("deleteSelected", { count: paths.length })}
          </Button>
        }
      />
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{t("deleteConfirmTitle")}</AlertDialogTitle>
          <AlertDialogDescription>{t("deleteConfirmDescription", { count: paths.length })}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{tCommon("cancel")}</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={isDeleting} onClick={handleConfirmDelete}>
            {t("delete")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

interface FolderTreeNodeProps {
  node: TagscanFolderNode;
  depth: number;
  selectedPath: string;
  onSelect: (path: string) => void;
}

function FolderTreeNode({ node, depth, selectedPath, onSelect }: FolderTreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const hasChildren = node.children.length > 0;

  return (
    <div>
      <button
        type="button"
        onClick={() => onSelect(node.path)}
        className={cn(
          "flex w-full items-center gap-1 rounded-md px-2 py-1 text-left text-sm hover:bg-accent",
          selectedPath === node.path && "bg-accent font-medium",
        )}
        style={{ paddingLeft: `${depth * 1 + 0.5}rem` }}
      >
        {hasChildren ? (
          <span
            role="button"
            aria-label={isExpanded ? "collapse" : "expand"}
            onClick={(event) => {
              event.stopPropagation();
              setIsExpanded((current) => !current);
            }}
            className="flex size-4 shrink-0 items-center justify-center"
          >
            {isExpanded ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
          </span>
        ) : (
          <span className="size-4 shrink-0" />
        )}
        <Folder className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span className="truncate">{node.name}</span>
      </button>

      {hasChildren && isExpanded && (
        <div>
          {node.children.map((child) => (
            <FolderTreeNode key={child.path} node={child} depth={depth + 1} selectedPath={selectedPath} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
}
