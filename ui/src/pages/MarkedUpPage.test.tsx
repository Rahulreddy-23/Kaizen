// @vitest-environment jsdom
import {act, cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {MemoryRouter, Route, Routes} from "react-router-dom";
import {api} from "../api";
import type {QuickKind, QuickView} from "../types";
import MarkedUpPage from "./MarkedUpPage";
import {notifyDataChanged} from "../lib/dataRefresh";

vi.mock('../api',()=>({api:{quickView:vi.fn(),getRun:vi.fn(),pageImageUrl:vi.fn(),annotatedUrl:vi.fn(),annotatedBundleUrl:vi.fn()}}));
vi.mock('../components/PageImage',()=>({PageImage:({src,alt}:{src:string|null;alt:string})=><div data-testid={alt}>{src ?? 'no page'}</div>}));

const kinds:QuickKind[]=['BOM','LABEL','DRAWING'];
const payload=():QuickView=>({sku:'SKU-A',groups:[{sku:'SKU-A',document_ids:kinds},{sku:'SKU-B',document_ids:['BOM']}],view:'components',
  documents:kinds.map(k=>({id:k,doc_type:k,file_name:`${k}.pdf`,pages:2,warnings:[],full_text:true,items:1})),
  rows:[],counts:{},total:0,offset:0,limit:100});

beforeEach(()=>{
  vi.clearAllMocks();
  vi.stubGlobal('requestAnimationFrame',(fn:()=>void)=>{fn();return 1;});
  vi.mocked(api.quickView).mockResolvedValue(payload());
  vi.mocked(api.getRun).mockResolvedValue({timestamp:'2026-10-24T09:15:00Z',last_decided_at:'2026-10-21T14:03:00Z'} as never);
  vi.mocked(api.pageImageUrl).mockImplementation((_r,d,p,_h,_dpi,_f,marks,revision)=>`${d}/page/${p}${marks?`?marks&revision=${revision}`:''}`);
  vi.mocked(api.annotatedUrl).mockImplementation((_r,d)=>`/annotated/${d}`);
  vi.mocked(api.annotatedBundleUrl).mockImplementation((_r,sku)=>`/annotated.zip?sku=${sku}`);
});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
const open=(url='/runs/run/marked-up')=>render(<MemoryRouter initialEntries={[url]}><Routes><Route path='/runs/:runId/marked-up' element={<MarkedUpPage/>}/></Routes></MemoryRouter>);

describe('marked-up documents',()=>{
 it('shows the three documents side by side, each page asked for with its marks drawn',async()=>{
  open();
  await screen.findAllByText('SKU-A');
  // The point of this page: the panes must ask for MARKED pages, not the originals.
  await waitFor(()=>expect(vi.mocked(api.pageImageUrl).mock.calls.length).toBeGreaterThan(0));
  const asked = vi.mocked(api.pageImageUrl).mock.calls;
  expect(asked.length).toBe(3);                       // one per document, 1 | 2 | 3
  expect(asked.every(call=>call[6]===true)).toBe(true);
  expect(asked.map(call=>call[1]).sort()).toEqual(['BOM','DRAWING','LABEL']);
 });

 it('offers every document on its own and all of them together',async()=>{
  open();
  const bundle = await screen.findByRole('link',{name:/Download all 3/});
  expect(bundle.getAttribute('href')).toBe('/annotated.zip?sku=SKU-A');
  for (const kind of ['BOM','Label','Diagram']) {
    const one = screen.getByRole('link',{name:`${kind} PDF`});
    expect(one.getAttribute('href')).toMatch(/^\/annotated\//);
    expect(one.hasAttribute('download')).toBe(true);
  }
 });

 it('dates the documents as dd-mm-yyyy, the way the stamp on the PDF reads',async()=>{
  open();
  // The newest decision, not the run date: the PDFs say the same, and two answers would be one too many.
  expect(await screen.findByText(/Updated 21-10-2026/)).toBeTruthy();
 });

 it('falls back to the run date when nobody has decided anything yet',async()=>{
  vi.mocked(api.getRun).mockResolvedValue({timestamp:'2026-10-24T09:15:00Z',last_decided_at:null} as never);
  open();
  expect(await screen.findByText(/Updated 24-10-2026/)).toBeTruthy();
 });

 it('refreshes the date and marked pages after a decision changes, preserving the selected page',async()=>{
  open();
  await screen.findByText(/Updated 21-10-2026/);
  fireEvent.change(screen.getByLabelText('BOM page'),{target:{value:'2'}});
  const before = screen.getByTestId('BOM.pdf, page 2').textContent;
  vi.mocked(api.getRun).mockResolvedValue({timestamp:'2026-10-24T09:15:00Z',last_decided_at:'2026-10-25T23:30:00Z'} as never);
  await act(async()=>{notifyDataChanged('/api/runs/run/decisions');});
  expect(await screen.findByText(/Updated 25-10-2026/)).toBeTruthy();
  await waitFor(()=>expect(screen.getByTestId('BOM.pdf, page 2').textContent).not.toBe(before));
  expect((screen.getByLabelText('BOM page') as HTMLSelectElement).value).toBe('2');
  expect(api.getRun).toHaveBeenCalledTimes(2);
 });

 it('tells the document page where the reader came from, so back returns here',async()=>{
  open('/runs/run/marked-up?sku=SKU-A');
  const [open_] = await screen.findAllByRole('link',{name:/Open .* document/});
  // Without this the document page sends them to the documents list, which they never visited.
  const href = open_.getAttribute('href') ?? '';
  expect(href).toContain('from=');
  expect(decodeURIComponent(href.split('from=')[1])).toBe('/runs/run/marked-up?sku=SKU-A');
 });

 it('explains what each colour means, because the label and drawing carry no legend of their own',async()=>{
  open();
  await screen.findAllByText('SKU-A');
  for (const meaning of [/Checked against the BOM/,/Checked against the label/,/Checked against the PKG drawing/,/Checked against the PCO/]) {
    expect(screen.getByText(meaning)).toBeTruthy();
  }
  // Colour says which document; shape says the result. A key that explains only the tick leaves a
  // reader guessing at the first cross they meet.
  expect(screen.getByText(/tick = agrees .* cross = differs .* no mark = needs a reviewer/)).toBeTruthy();
 });
});
