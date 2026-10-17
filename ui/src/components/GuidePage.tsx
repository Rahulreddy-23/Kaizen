import { ArrowLeft, ArrowRight, DownloadSimple } from "@phosphor-icons/react";
import { useEffect, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useReviewer } from "../lib/reviewer";
import { Button, LinkButton, PageHeader } from "./ui";

export interface Guide {
  title: string;
  description: string;
  sections: {
    id: string;
    label: string;
    intro: string;
    steps: {title: string; body: string}[];
    paragraphs: string[];
    note: string;
    action: {label: string; to: string} | null;
    audience: string;
  }[];
}

export function GuidePage({ guide, policy = false }: {guide: Guide; policy?: boolean}) {
  const [params, setParams] = useSearchParams();
  const {session} = useReviewer();
  const active = guide.sections.find(s => s.id === params.get("topic")) ?? guide.sections[0];
  const index = guide.sections.indexOf(active);
  const all = policy || params.get("view") === "all";
  const heading = useRef<HTMLHeadingElement>(null);
  const previous = useRef(`${active.id}:${all}`);
  useEffect(() => {
    const next = `${active.id}:${all}`;
    if (previous.current !== next) {
      heading.current?.focus({preventScroll: true});
      heading.current?.scrollIntoView({block: "start"});
      previous.current = next;
    }
  }, [active.id, all]);
  const download = () => {
    const text = [`# ${guide.title}`, guide.description, ...guide.sections.flatMap(s => [
      `## ${s.label}`, s.intro, ...(s.audience ? [`For: ${s.audience}.`] : []), ...s.paragraphs,
      ...s.steps.map((step, i) => `${i + 1}. **${step.title}.** ${step.body}`), ...(s.note ? [s.note] : []),
    ])].join("\n\n") + "\n";
    const url = URL.createObjectURL(new Blob([text], {type: "text/markdown;charset=utf-8"}));
    const link = document.createElement("a");
    link.href = url; link.download = policy ? "kaizen-privacy.md" : "kaizen-user-guide.md"; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return <div className="guide-page">
    <PageHeader title={guide.title} description={guide.description} actions={<>
      <Button icon={<DownloadSimple size={16} />} onClick={download}>{policy ? "Download notice" : "Download guide"}</Button>
      {!policy && <Button aria-pressed={all} onClick={() => setParams(all ? {topic: active.id} : {topic: active.id, view: "all"})}>{all ? "Read by topic" : "Read all topics"}</Button>}
    </>} />
    <div className={`guide-grid ${policy ? "guide-policy" : ""}`}>
      {!policy && <>
        <nav aria-label="Tutorial topics" className="guide-index"><h2>In this guide</h2>{guide.sections.map(s => <Link key={s.id} to={`?topic=${s.id}`} aria-current={!all && s.id === active.id ? "page" : undefined}>{s.label}</Link>)}</nav>
        <div className="guide-mobile-index"><label className="label" htmlFor="guide-topic">Choose a topic</label><select id="guide-topic" className="input w-full" value={all ? "all" : active.id} onChange={e => setParams(e.target.value === "all" ? {view: "all"} : {topic: e.target.value})}><option value="all">Read all topics</option>{guide.sections.map(s => <option key={s.id} value={s.id}>{s.label}</option>)}</select></div>
      </>}
      <div className="guide-reader">
        <div className="guide-chapters">{(all ? guide.sections : [active]).map((s, i) => <article key={s.id} className="guide-chapter" aria-labelledby={`guide-${s.id}`}>
          <h2 id={`guide-${s.id}`} tabIndex={-1} ref={i === 0 ? heading : undefined}>{s.label}</h2>
          {s.audience && <p className="guide-audience">For {s.audience.toLowerCase()}</p>}
          <p className="guide-intro">{s.intro}</p>
          {s.paragraphs.map(p => <p key={p}>{p}</p>)}
          {s.steps.length > 0 && <ol className="guide-steps">{s.steps.map(step => <li key={step.title}><h3>{step.title}</h3><p>{step.body}</p></li>)}</ol>}
          {s.note && <p className="guide-note">{s.note}</p>}
          {s.action && (!s.audience || session?.is_admin) && <LinkButton to={s.action.to} iconRight={<ArrowRight size={16} />}>{s.action.label}</LinkButton>}
        </article>)}</div>
        {!all && <nav aria-label="Tutorial chapter navigation" className="guide-pagination">
          {index > 0 ? <LinkButton to={`?topic=${guide.sections[index - 1].id}`} icon={<ArrowLeft size={16} />}>{guide.sections[index - 1].label}</LinkButton> : <span />}
          {index < guide.sections.length - 1 && <LinkButton to={`?topic=${guide.sections[index + 1].id}`} iconRight={<ArrowRight size={16} />}>{guide.sections[index + 1].label}</LinkButton>}
        </nav>}
        <p className="guide-footer">{policy ? <>Last reviewed 16 October 2026. Provider details: <a href="https://render.com/security" target="_blank" rel="noreferrer">Render security</a>, <a href="https://render.com/docs/disks" target="_blank" rel="noreferrer">disk encryption</a> and <a href="https://render.com/dpa" target="_blank" rel="noreferrer">data processing agreement</a>.</> : <>Need the data-handling details? Read <Link to="/privacy">Privacy and document handling</Link>.</>}</p>
      </div>
    </div>
  </div>;
}
