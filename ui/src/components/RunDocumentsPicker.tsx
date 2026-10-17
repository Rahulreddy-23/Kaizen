import { File, FilePdf, FileXls, FolderOpen, X } from "@phosphor-icons/react";
import { useRef } from "react";
import { Button } from "./ui";

const DIR_PROPS = { webkitdirectory: "", directory: "" } as Record<string, string>;

function fileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.ceil(bytes / 1024).toLocaleString()} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function RunDocumentsPicker({ files, disabled, onSelect, onRemove, onClear }: {
  files: File[];
  disabled: boolean;
  onSelect: (files: FileList) => void;
  onRemove: (index: number) => void;
  onClear: () => void;
}) {
  const folderInput = useRef<HTMLInputElement>(null);
  const filesInput = useRef<HTMLInputElement>(null);
  const selected = files.length > 0;
  const choose = (input: HTMLInputElement) => {
    // Cancelling a picker keeps the current selection. Reset after selection so the same files
    // can be chosen again after removal, without losing their retained relative paths.
    if (input.files?.length) onSelect(input.files);
    input.value = "";
  };

  return <section className="run-documents" aria-label="Documents to check">
    <input ref={folderInput} type="file" multiple {...DIR_PROPS} hidden disabled={disabled}
      onChange={e => choose(e.currentTarget)} aria-label="Project folder" />
    <input ref={filesInput} type="file" multiple accept=".pdf,.xlsx,.xlsm,.csv" hidden disabled={disabled}
      onChange={e => choose(e.currentTarget)} aria-label="Individual documents" />
    <div className={`document-picker ${selected ? "has-files" : ""}`}>
      <FolderOpen className="document-picker-icon" size={36} weight="duotone" aria-hidden />
      <div className="document-picker-copy">
        <h3>{selected ? "Replace selected documents" : "Please upload your project documents"}</h3>
        <p>Choose a folder with SKU subfolders, or select individual BOMs, labels, drawings and PCOs.</p>
      </div>
      <div className="document-picker-actions">
        <Button icon={<FolderOpen size={18} />} disabled={disabled} onClick={() => folderInput.current?.click()}>Choose folder</Button>
        <Button icon={<File size={18} />} disabled={disabled} onClick={() => filesInput.current?.click()}>Choose files</Button>
      </div>
      <p className="document-picker-hint">PDF, XLSX, XLSM and CSV · Up to 250 MB per run</p>
      {!selected && <p className="document-picker-paths">Folder structure is preserved.</p>}
    </div>
    {selected && <div className="upload-selection">
      <div className="upload-selection-heading">
        <div role="status"><strong>{files.length} {files.length === 1 ? "document" : "documents"} selected</strong><span>{fileSize(files.reduce((sum, file) => sum + file.size, 0))} total</span></div>
        <Button variant="ghost" size="sm" disabled={disabled} onClick={onClear}>Clear all</Button>
      </div>
      <ul className="upload-file-list" aria-label="Documents selected for upload">
        {files.map((file, index) => {
          const relativePath = file.webkitRelativePath || file.name;
          const parent = relativePath.includes("/") ? relativePath.slice(0, relativePath.lastIndexOf("/")) : "";
          const Icon = /\.pdf$/i.test(file.name) ? FilePdf : FileXls;
          return <li key={`${relativePath}:${index}`}>
            <Icon size={22} aria-hidden />
            <div className="upload-file-name"><strong>{file.name}</strong>{parent && <span>{parent}</span>}</div>
            <small>{fileSize(file.size)}</small>
            <Button variant="ghost" size="sm" iconOnly disabled={disabled} aria-label={`Remove ${relativePath}`} icon={<X size={16} />} onClick={() => onRemove(index)} />
          </li>;
        })}
      </ul>
    </div>}
  </section>;
}
