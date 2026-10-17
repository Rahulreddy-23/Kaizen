import type { DocumentSummary, SkuGroup } from "../types";
import { familyOf } from "./format";

export interface DocumentGroup {
  key: string;
  label: string;
  sku: string | null;
  docs: DocumentSummary[];
  items: number;
  warnings: number;
}

/** Group by the run's actual SKU associations, including retained evidence copies. */
export function groupDocuments(documents: DocumentSummary[], groups: SkuGroup[], query = ""): DocumentGroup[] {
  const byId = new Map(documents.map(document => [document.id, document]));
  const memberships = new Map<string, Set<string>>();
  for (const group of groups) for (const id of group.document_ids) {
    const hash = byId.get(id)?.sha256;
    if (!hash) continue;
    const skus = memberships.get(hash) ?? new Set<string>();
    skus.add(group.sku);
    memberships.set(hash, skus);
  }
  const needle = query.trim().toLowerCase();
  const result = new Map<string, DocumentGroup>();
  for (const document of documents) {
    let skus = [...(memberships.get(document.sha256) ?? [])];
    if (!skus.length && document.sku) {
      const familyMatches = groups.filter(group => group.sku === document.sku || familyOf(group.sku) === familyOf(document.sku!));
      if (familyMatches.length === 1) skus = [familyMatches[0].sku];
    }
    const sku = skus.length === 1 ? skus[0] : null;
    const key = sku ?? (skus.length > 1 ? "shared" : "unassigned");
    const label = sku ? `SKU ${sku}` : key === "shared" ? "Shared source documents" : "Other source documents";
    if (needle && ![document.file_name, document.file, document.sku ?? "", document.doc_type, document.parser, ...skus, label].some(value => value.toLowerCase().includes(needle))) continue;
    const group = result.get(key) ?? {key, label, sku, docs: [], items: 0, warnings: 0};
    group.docs.push(document); group.items += document.items; group.warnings += document.warnings.length;
    result.set(key, group);
  }
  const order = {BOM: 0, LABEL: 1, DRAWING: 2, PCO: 3};
  return [...result.values()].sort((a, b) => Number(!a.sku) - Number(!b.sku) || a.label.localeCompare(b.label)).map(group => ({...group,
    docs: group.docs.sort((a, b) => order[a.doc_type] - order[b.doc_type] || a.file_name.localeCompare(b.file_name) || a.file.localeCompare(b.file)),
  }));
}
