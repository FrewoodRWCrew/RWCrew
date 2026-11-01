"use client";

// The Scans module's "JSON source files" screen: the same browser as the CSV
// Source Files screen, on the folder with one .json file per wristband message
// (one subfolder per day). A separate client component because a server page
// can't hand FileBrowser its API functions.

import type { TagscanFileEntry, TagscanFolderNode } from "@/lib/types";
import {
  deleteWristbandFiles,
  getWristbandFileContent,
  getWristbandFolderTree,
  listWristbandFiles,
} from "@/lib/api";
import { FileBrowser, type FileBrowserApi } from "@/components/module-1/file-browser";

const WRISTBAND_FILES_API: FileBrowserApi = {
  getTree: getWristbandFolderTree,
  listFiles: listWristbandFiles,
  getContent: getWristbandFileContent,
  deleteFiles: deleteWristbandFiles,
};

interface WristbandFileBrowserProps {
  initialTree: TagscanFolderNode;
  initialFolderPath: string;
  initialFiles: TagscanFileEntry[];
  canDelete: boolean;
}

export function WristbandFileBrowser(props: WristbandFileBrowserProps) {
  return <FileBrowser {...props} api={WRISTBAND_FILES_API} messagesNamespace="wristband.files" />;
}
