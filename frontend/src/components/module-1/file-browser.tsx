"use client";

// TagScan's "Dashboard" screen: a read-only, Explorer-style browser over
// the folder where incoming CSV scan files currently land. Three panes:
//   1. Folder tree (left) — the whole folder structure.
//   2. File list (middle) — files directly inside whichever folder is
//      selected in the tree.
//   3. Content preview (right) — a "notepad"-style read-only view of
//      whichever file is selected in the file list.
// Purely for looking at what has arrived so far — parsing/importing the
// CSV data into the database is a later step.

import { useCallback, useState } from "react";
import { ChevronDown, ChevronRight, File, Folder, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { ApiError, getTagscanFileContent, getTagscanFolderTree, listTagscanFiles } from "@/lib/api";
import type { TagscanFileContent, TagscanFileEntry, TagscanFolderNode } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FileBrowserProps {
  initialTree: TagscanFolderNode;
  initialFiles: TagscanFileEntry[];
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileBrowser({ initialTree, initialFiles }: FileBrowserProps) {
  const t = useTranslations("tagscan.dashboard");

  const [tree, setTree] = useState(initialTree);
  const [selectedFolderPath, setSelectedFolderPath] = useState<string>(initialTree.path);
  const [files, setFiles] = useState<TagscanFileEntry[]>(initialFiles);
  const [filesError, setFilesError] = useState<string | null>(null);

  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<TagscanFileContent | null>(null);
  const [contentError, setContentError] = useState<string | null>(null);
  const [isLoadingContent, setIsLoadingContent] = useState(false);

  const loadFiles = useCallback(
    async (folderPath: string) => {
      setFilesError(null);
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
          <div className="border-b bg-muted/50 px-3 py-2 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            {t("filesHeading")}
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
