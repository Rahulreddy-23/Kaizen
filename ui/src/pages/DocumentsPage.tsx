import { ArrowsClockwise, Eye, FileArrowDown, Files, MagnifyingGlass } from "@phosphor-icons/react";
import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Badge, DocTypeBadge } from "../components/Badges";
import { ErrorBox } from "../components/Feedback";
import { AnchorButton, Button, Card, CardHead, EmptyState, LinkButton, PageHeader, TableSkeleton } from "../components/ui";
import { enc, isPdf, shortSha } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { groupDocuments } from "../lib/documentGroups";

/** Number of columns in the table below: the SKU group header spans all of them. */
const SPAN = 6;

const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

export default function DocumentsPage() {
  const { runId = "" } = useParams();
  const access = useAsync(() => api.getRun(runId), [runId]);
  const nav = useNavigate();
  const docs = useAsync(() => api.getDocuments(runId), [runId]);
  const [filter, setFilter] = useState("");

  const groups = useMemo(() => groupDocuments(docs.data ?? [], access.data?.groups ?? [], filter), [docs.data, access.data?.groups, filter]);
  const allGroups = useMemo(() => groupDocuments(docs.data ?? [], access.data?.groups ?? []), [docs.data, access.data?.groups]);

  const all = docs.data ?? [];
  const shown = groups.reduce((n, g) => n + g.docs.length, 0);
  const lines = all.reduce((n, d) => n + d.items, 0);
  const warnings = all.reduce((n, d) => n + d.warnings.length, 0);
  const filtering = filter.trim().length > 0;

  return (
    <div>
      <PageHeader
        back={{ to: `/runs/${enc(runId)}`, label: "Overview" }}
        title="Documents"
        description="Source documents grouped by SKU. Open a file to check the extracted text."
        meta={
          docs.data && (
            <>
              <span>{plural(all.length, "document")}</span>
              <span>{plural(lines, "extracted line")}</span>
              <span className={warnings ? "text-warn-strong" : undefined}>{plural(warnings, "parser warning")}</span>
              <span>{plural(allGroups.filter(group => group.sku).length, "SKU set")}</span>
            </>
          )
        }
        actions={
          <><LinkButton to={`/runs/${enc(runId)}/quick-view`} icon={<Eye size={16} />}>Quick view</LinkButton><Button variant="ghost" onClick={docs.reload} loading={docs.loading && docs.data !== null} icon={<ArrowsClockwise size={16} />}>
            Refresh
          </Button></>
        }
      />

      <div className="space-y-5 stagger">
        <Card>
          <CardHead
            title="Source documents"
            description=""
            count={docs.data ? (filtering ? `${shown} of ${all.length}` : all.length) : undefined}
            icon={<Files size={18} />}
            actions={
              <div className="relative">
                <MagnifyingGlass size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3 pointer-events-none" aria-hidden />
                <input className="input input-sm pl-8 w-56" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Filter by file, SKU or parser" aria-label="Filter documents by file name, SKU or parser" />
              </div>
            }
          />

          {docs.loading && !docs.data && <TableSkeleton rows={8} cols={7} />}
          {(docs.error || access.error) && (
            <div className="p-4">
              <ErrorBox error={docs.error || access.error || ""} onRetry={() => {docs.reload(); access.reload();}} />
            </div>
          )}

          {docs.data &&
            (all.length === 0 ? (
              <EmptyState
                icon={<Files size={36} />}
                title="No documents found"
                description="Start a new cross-check with BOM, label, drawing or PCO files."
                action={
                  <LinkButton to="/" variant="primary">
                    All runs
                  </LinkButton>
                }
              />
            ) : shown === 0 ? (
              <EmptyState
                icon={<MagnifyingGlass size={36} />}
                title="No document matches that filter"
                description={`Clear the filter to see all ${plural(all.length, "document")} in this run.`}
                action={<Button onClick={() => setFilter("")}>Clear filter</Button>}
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>File</th>
                      <th className="text-right">Lines</th>
                      <th className="text-right">Pages</th>
                      <th>Warnings</th>
                      <th className="text-right">Open</th>
                    </tr>
                  </thead>
                  {groups.map((g) => (
                    <tbody key={g.key}>
                      <tr>
                        <td colSpan={SPAN} className="bg-surface-2 py-2 border-b border-line">
                          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                            {g.sku ? (
                              <>
                                <span className="text-xs font-medium text-ink-2">SKU set</span>
                                <span className="mono text-sm font-semibold text-ink">{g.sku}</span>
                              </>
                            ) : (
                              <span className="text-sm font-semibold text-ink">{g.label}</span>
                            )}
                            <span className="text-xs text-ink-3">
                              {plural(g.docs.length, "document")} · {plural(g.items, "line")}
                            </span>
                            {g.warnings > 0 && <Badge tone="warn">{plural(g.warnings, "parser warning")}</Badge>}
                          </div>
                        </td>
                      </tr>
                      {g.docs.map((d) => {
                        const to = `/runs/${enc(runId)}/documents/${enc(d.id)}`;
                        return (
                          <tr key={d.id} className="clickable" onClick={() => nav(to)}>
                            <td>
                              <DocTypeBadge value={d.doc_type} />
                            </td>
                            <td className="min-w-[15rem]">
                              <Link className="document-name font-medium" to={to} onClick={(e) => e.stopPropagation()}>
                                {d.file_name}
                              </Link>
                              <details className="mt-1 text-xs text-ink-3 max-w-[24rem]" onClick={event => event.stopPropagation()}><summary className="cursor-pointer">Source details</summary><dl className="mt-2 space-y-1"><div><dt className="inline font-medium">Parser: </dt><dd className="inline">{d.parser} v{d.parser_version}</dd></div><div><dt className="inline font-medium">File: </dt><dd className="inline break-all">{d.file}</dd></div><div><dt className="inline font-medium">SHA-256: </dt><dd className="inline mono break-all" title={d.sha256}>{shortSha(d.sha256)}</dd></div></dl></details>
                            </td>
                            <td className="text-right num">{d.items}</td>
                            <td className="text-right num text-ink-2">{d.pages > 0 ? d.pages : <span className="text-xs text-ink-3">Spreadsheet</span>}</td>
                            <td className="max-w-[22rem]">
                              {d.warnings.length === 0 ? (
                                <span className="text-ink-4">—</span>
                              ) : (
                                <>
                                  <details className="document-warnings"><summary>{plural(d.warnings.length, "warning")}</summary><ul className="list-disc pl-4 mt-2 space-y-1 text-xs text-warn-strong">{d.warnings.map((warning, index) => <li key={index}>{warning}</li>)}</ul></details>
                                </>
                              )}
                            </td>
                            <td className="whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                              <div className="flex items-center justify-end gap-1.5">
                                <LinkButton size="sm" to={to} icon={<Eye size={16} />}>
                                  Document
                                </LinkButton>
                                {["BOM", "LABEL", "DRAWING"].includes(d.doc_type) && d.header?.revision_role !== "old" && isPdf(d.file_name) && access.data && access.data.permission !== "view" && (
                                  <AnchorButton size="sm" href={api.annotatedUrl(runId, d.id)} download icon={<FileArrowDown size={16} />} title="PDF with check marks from the reviewer decisions">
                                    Annotated
                                  </AnchorButton>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  ))}
                </table>
              </div>
            ))}
        </Card>
      </div>
    </div>
  );
}
