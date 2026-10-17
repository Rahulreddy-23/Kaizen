const SUPPORTED = /\.(pdf|xlsx|xlsm|csv)$/i;
export const MAX_RUN_BYTES = 250 * 1024 * 1024;
// One SKU set per folder: a BOM, a label and a drawing. Names are free-form, so the browser can only
// count documents; the server identifies each one from its content.
export const FILES_PER_FOLDER = 3;

export interface UploadFolder {
  /** Unique within the selection; also the upload path prefix, so same-named folders cannot collide. */
  name: string;
  files: File[];
  /** Chosen as individual files rather than a folder; the server still receives them under `name`. */
  loose?: boolean;
}

const uniqueName = (taken: UploadFolder[], base: string) => {
  let name = base;
  for (let n = 2; taken.some(f => f.name === name); n++) name = `${base} (${n})`;
  return name;
};

export function supportedRunFiles(files: File[]): File[] {
  return files.filter(file => SUPPORTED.test(file.name) && !file.name.startsWith(".") && !file.name.startsWith("~$"));
}

// The folder's own name plus each file, so differently named folders holding identical copies stay apart,
// while one folder picked twice (directly, or once through its parent) is recognised as the same.
const ownFolder = (file: File) => (file.webkitRelativePath || "").split("/").slice(-2, -1)[0] ?? "";
const signature = (folder: UploadFolder) => folder.files.map(f => `${ownFolder(f)}/${f.name}:${f.size}:${f.lastModified}`).sort().join("|");

/** Adds one folder pick to the selection: one entry per directory that directly holds documents. */
export function addFolders(current: UploadFolder[], picked: File[]): UploadFolder[] {
  const byDir = new Map<string, File[]>();
  for (const file of supportedRunFiles(picked)) {
    const path = file.webkitRelativePath || file.name;
    const dir = path.includes("/") ? path.slice(0, path.lastIndexOf("/")) : "";
    byDir.set(dir, [...(byDir.get(dir) ?? []), file]);
  }
  const next = [...current];
  const seen = new Set(current.map(signature));
  for (const [dir, files] of [...byDir].sort(([a], [b]) => a.localeCompare(b))) {
    const folder = { name: dir, files };
    if (seen.has(signature(folder))) continue;
    seen.add(signature(folder));
    next.push({ name: uniqueName(next, dir), files });
  }
  return next;
}

/** Adds one pick of individual files as one run. They must be chosen together, exactly 3 at once. */
export function addFileSet(current: UploadFolder[], picked: File[]): { folders: UploadFolder[]; problem: string | null } {
  const files = supportedRunFiles(picked);
  if (files.length !== FILES_PER_FOLDER) return { folders: current, problem: `Select exactly 3 files at once: a BOM, a label and a drawing. You selected ${files.length} supported file${files.length === 1 ? "" : "s"}.` };
  const set = { name: "", files };
  if (current.some(f => signature(f) === signature(set))) return { folders: current, problem: "Those files are already added." };
  return { folders: [...current, { name: uniqueName(current, "Selected files"), files, loose: true }], problem: null };
}

export function folderProblem(folder: UploadFolder): string | null {
  if (!folder.name) return "These documents are not inside a folder. Choose a folder instead.";
  if (folder.files.length !== FILES_PER_FOLDER) return `Has ${folder.files.length} document${folder.files.length === 1 ? "" : "s"}; needs exactly 3: a BOM, a label and a drawing.`;
  return null;
}

export function uploadProblem(folders: UploadFolder[]): string | null {
  if (!folders.length) return "Choose a folder containing a BOM, a label and a drawing (PDF, XLSX, XLSM or CSV).";
  const bad = folders.filter(folderProblem);
  if (bad.length) return `${bad.length === 1 ? `Folder '${bad[0].name}'` : `${bad.length} folders`} ${bad.length === 1 ? "does" : "do"} not have exactly 3 documents. Each folder needs a BOM, a label and a drawing.`;
  const big = folders.find(folder => folder.files.reduce((total, file) => total + file.size, 0) > MAX_RUN_BYTES);
  if (big) return `Folder '${big.name}' is over 250 MB; each run can upload at most 250 MB.`;
  return null;
}
