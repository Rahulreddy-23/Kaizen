// @vitest-environment jsdom
import {act, cleanup, fireEvent, render, screen, waitFor, within} from "@testing-library/react";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {MemoryRouter, Route, Routes} from "react-router-dom";
import {api} from "../api";
import type {QuickCell, QuickKind, QuickStatus, QuickView} from "../types";
import QuickViewPage from "./QuickViewPage";
import {notifyDataChanged} from "../lib/dataRefresh";

vi.mock('../api',()=>({api:{quickView:vi.fn(),pageImageUrl:vi.fn()}}));
vi.mock('../components/PageImage',()=>({PageImage:({src,bbox,tone,alt,zoom,fit,dpi}:{src:string|null;bbox:unknown;tone:string;alt:string;zoom:number;fit:boolean;dpi:number})=><div data-zoom={zoom} data-fit={String(fit)} data-dpi={dpi} data-testid={alt} data-box={JSON.stringify(bbox)} data-tone={tone}>{src ?? 'Spreadsheet preview'}</div>}));
beforeEach(()=>{vi.clearAllMocks();vi.stubGlobal('requestAnimationFrame',(fn:()=>void)=>{fn();return 1;});vi.mocked(api.pageImageUrl).mockImplementation((_r,d,p)=>`${d}/page/${p}`);});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
const kinds:QuickKind[]=['BOM','LABEL','DRAWING'];
const names=['BOM','Label','Diagram'];
const cell=(kind:QuickKind,status:QuickStatus='matched',page=1):QuickCell=>({status,items:[{id:`${kind}:item`,doc_id:kind,doc_type:kind,file:`${kind}.pdf`,file_name:`${kind}.pdf`,sha256:'a'.repeat(64),page,bbox:{x0:20,y0:30,x1:100,y1:42},raw_text:'Original raw cover',locator:'page source line',sheet:null,item_number:kind==='BOM'?'CAP001':null,description:`${kind} protective cover`,quantity:kind==='DRAWING'?null:'1',uom:'EA',oper_seq:null,category:'PHYSICAL_COMPONENT',category_reason:'Component',confidence:.95,attributes:{},sub_quantity:null}]});
const payload=():QuickView=>({sku:'SKU-A',groups:[{sku:'SKU-A',document_ids:kinds},{sku:'SKU-B',document_ids:['BOM']}],view:'components',documents:kinds.map(k=>({id:k,doc_type:k,file_name:`${k}.pdf`,pages:3,warnings:[],full_text:true,items:1})),rows:[{id:'one',status:'matched',cells:{BOM:cell('BOM'),LABEL:cell('LABEL','matched',2),DRAWING:cell('DRAWING','matched',3)},checks:[{row_id:'pair',check:'BOM_LABEL',status:'matched',classification:'EXACT',engine_classification:'EXACT',state:'ENGINE_RECOMMENDED',explanation:'Recorded source pairing',findings:[],merged_rows:1}]}],counts:{matched:1,attention:0,neutral:0},total:1,offset:0,limit:100});
const open=(url='/runs/run/quick-view')=>render(<MemoryRouter initialEntries={[url]}><Routes><Route path='/runs/:runId/quick-view' element={<QuickViewPage/>}/></Routes></MemoryRouter>);

describe('SKU quick view',()=>{
 it('refreshes status without blanking entries or resetting a manually chosen page',async()=>{
  let finish!: (value:QuickView)=>void;
  vi.mocked(api.quickView).mockResolvedValueOnce(payload()).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));open();
  fireEvent.click(await screen.findByRole('button',{name:'Show BOM source for row 1'}));
  fireEvent.change(screen.getByRole('combobox',{name:'BOM page'}),{target:{value:'3'}});
  fireEvent.change(screen.getByRole('combobox',{name:'BOM zoom'}),{target:{value:'150'}});
  act(()=>notifyDataChanged('/api/runs/run/decisions'));
  await waitFor(()=>expect(api.quickView).toHaveBeenCalledTimes(2));
  expect(screen.queryByText('Loading entries…')).toBeNull();
  expect(screen.getByRole('button',{name:'Show BOM source for row 1'})).toBeTruthy();
  const next=payload();next.rows[0].status='attention';next.rows[0].cells.BOM!.status='attention';
  await act(async()=>finish(next));
  expect((screen.getByRole('combobox',{name:'BOM page'}) as HTMLSelectElement).value).toBe('3');
  expect((screen.getByRole('combobox',{name:'BOM zoom'}) as HTMLSelectElement).value).toBe('150');
  expect(screen.getByTestId('BOM.pdf, page 3').getAttribute('data-tone')).toBe('attention');
 });
 it('focuses a source from the selected pair and restores that pair from the toolbar',async()=>{
  vi.mocked(api.quickView).mockResolvedValue(payload());open();
  fireEvent.click(await screen.findByRole('button',{name:'Open document reader'}));
  const dialog=screen.getByRole('dialog',{name:'Source documents'});
  fireEvent.click(within(dialog).getByRole('button',{name:'Two documents'}));
  fireEvent.change(within(dialog).getByRole('combobox',{name:'Document pair'}),{target:{value:'2'}});
  fireEvent.click(within(dialog).getByRole('button',{name:'Focus'}));
  expect(within(dialog).getByRole('region',{name:'Label source preview'})).toBeTruthy();
  expect(within(dialog).queryByRole('region',{name:'BOM source preview'})).toBeNull();
  fireEvent.click(within(dialog).getByRole('button',{name:'Restore split view'}));
  expect(within(dialog).getByRole('region',{name:'Diagram source preview'})).toBeTruthy();
  expect(within(dialog).queryByRole('region',{name:'BOM source preview'})).toBeNull();
 });
 it('opens a full-window reading workspace, keeps zoom independent and restores keyboard focus',async()=>{
  const p=payload();p.rows.push({...p.rows[0],id:'two',cells:{BOM:cell('BOM','attention',2),LABEL:null,DRAWING:null},checks:[],status:'attention'});p.total=2;
  vi.mocked(api.quickView).mockResolvedValue(p);open();
  fireEvent.click(await screen.findByRole('button',{name:'Show BOM source for row 1'}));
  const expand=screen.getByRole('button',{name:'Open document reader'});expand.focus();fireEvent.click(expand);
  const dialog=screen.getByRole('dialog',{name:'Source documents'});
  expect(dialog.className).toContain('quick-document-dialog');
  const bom=within(dialog).getByRole('combobox',{name:'BOM zoom'});
  expect((bom as HTMLSelectElement).value).toBe('200');
  fireEvent.change(bom,{target:{value:'200'}});
  expect(within(dialog).getByTestId('BOM.pdf, page 1').getAttribute('data-zoom')).toBe('200');
  expect(within(dialog).getByTestId('LABEL.pdf, page 2').getAttribute('data-zoom')).toBe('125');
  expect(api.pageImageUrl).toHaveBeenCalledWith('run','BOM',1,null,300,'png',undefined,undefined);  // review shows the documents unmarked
  expect(api.pageImageUrl).toHaveBeenCalledWith('run','LABEL',2,null,300,'jpeg',undefined,undefined);
  fireEvent.change(bom,{target:{value:'fit'}});
  expect(within(dialog).getByTestId('BOM.pdf, page 1').getAttribute('data-fit')).toBe('true');
  fireEvent.click(within(dialog).getByRole('button',{name:'Next entry'}));
  await waitFor(()=>expect(within(dialog).getByTestId('BOM.pdf, page 2').getAttribute('data-tone')).toBe('attention'));
  fireEvent.click(within(dialog).getByRole('button',{name:'Previous entry'}));
  await waitFor(()=>expect(within(dialog).getByTestId('BOM.pdf, page 1').getAttribute('data-tone')).toBe('matched'));
  fireEvent.keyDown(document,{key:'Escape'});
  expect(screen.queryByRole('dialog')).toBeNull();
  expect(document.activeElement).toBe(expand);
  expect(document.body.style.overflow).not.toBe('hidden');
 });
 it('resizes splits with the keyboard and preserves pages and zoom across paired and focused layouts',async()=>{
  vi.mocked(api.quickView).mockResolvedValue(payload());open();
  fireEvent.click(await screen.findByRole('button',{name:'Show Label source for row 1'}));
  fireEvent.click(screen.getByRole('button',{name:'Open document reader'}));
  const dialog=screen.getByRole('dialog',{name:'Source documents'});
  const divider=within(dialog).getByRole('separator',{name:'Resize BOM and Label panes'});
  fireEvent.keyDown(divider,{key:'ArrowRight'});expect(divider.getAttribute('aria-valuenow')).toBe('55');
  fireEvent.keyDown(divider,{key:'End'});expect(divider.getAttribute('aria-valuenow')).toBe('75');
  fireEvent.doubleClick(divider);expect(divider.getAttribute('aria-valuenow')).toBe('50');
  vi.stubGlobal('PointerEvent',MouseEvent);
  Object.defineProperty(divider.parentElement,'clientWidth',{configurable:true,value:1000});
  fireEvent.pointerDown(divider,{button:0,clientX:100});fireEvent.pointerMove(divider,{clientX:200});fireEvent.pointerUp(divider);
  expect(divider.getAttribute('aria-valuenow')).toBe('65');
  fireEvent.pointerMove(divider,{clientX:300});expect(divider.getAttribute('aria-valuenow')).toBe('65');
  fireEvent.click(within(dialog).getByRole('button',{name:'Reset widths'}));
  expect(divider.getAttribute('aria-valuenow')).toBe('50');
  fireEvent.change(within(dialog).getByRole('combobox',{name:'BOM page'}),{target:{value:'3'}});
  fireEvent.change(within(dialog).getByRole('combobox',{name:'BOM zoom'}),{target:{value:'150'}});
  fireEvent.click(within(dialog).getByRole('button',{name:'Two documents'}));
  fireEvent.change(within(dialog).getByRole('combobox',{name:'Document pair'}),{target:{value:'1'}});
  expect(within(dialog).queryByRole('region',{name:'Label source preview'})).toBeNull();
  expect(within(dialog).getByRole('region',{name:'Diagram source preview'})).toBeTruthy();
  fireEvent.click(within(dialog).getByRole('button',{name:'Focus BOM'}));
  expect(within(dialog).queryByRole('region',{name:'Diagram source preview'})).toBeNull();
  expect((within(dialog).getByRole('combobox',{name:'BOM page'}) as HTMLSelectElement).value).toBe('3');
  expect((within(dialog).getByRole('combobox',{name:'BOM zoom'}) as HTMLSelectElement).value).toBe('150');
  fireEvent.click(within(dialog).getByRole('button',{name:'Label'}));
  expect(within(dialog).getByRole('region',{name:'Label source preview'})).toBeTruthy();
  fireEvent.click(within(dialog).getByRole('button',{name:'Restore split view'}));
  expect(within(dialog).getByRole('region',{name:'BOM source preview'})).toBeTruthy();
  expect(within(dialog).getByRole('region',{name:'Diagram source preview'})).toBeTruthy();
  expect(within(dialog).queryByRole('region',{name:'Label source preview'})).toBeNull();
  fireEvent.click(within(dialog).getByRole('button',{name:'Locate selected'}));
  expect((within(dialog).getByRole('combobox',{name:'BOM page'}) as HTMLSelectElement).value).toBe('1');
  expect((within(dialog).getByRole('combobox',{name:'BOM zoom'}) as HTMLSelectElement).value).toBe('150');
  fireEvent.change(within(dialog).getByRole('combobox',{name:'Document pair'}),{target:{value:'2'}});
  fireEvent.click(within(dialog).getByRole('button',{name:'Focus'}));
  expect(within(dialog).getByRole('region',{name:'Label source preview'})).toBeTruthy();
  expect(within(dialog).queryByRole('region',{name:'BOM source preview'})).toBeNull();
  fireEvent.click(within(dialog).getByRole('button',{name:'Restore split view'}));
  expect(within(dialog).getByRole('region',{name:'Diagram source preview'})).toBeTruthy();
  expect(within(dialog).queryByRole('region',{name:'BOM source preview'})).toBeNull();
 });
 it('uses full-width source tabs in a narrow container',async()=>{
  vi.spyOn(HTMLElement.prototype,'clientWidth','get').mockReturnValue(390);
  vi.stubGlobal('ResizeObserver',class {constructor(private cb:()=>void){}observe(){this.cb();}disconnect(){}});
  vi.mocked(api.quickView).mockResolvedValue(payload());open();
  await screen.findByRole('group',{name:'Focused source'});
  expect(screen.queryByRole('region',{name:'Label source preview'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Label'}));
  expect(screen.getByRole('region',{name:'Label source preview'})).toBeTruthy();
  expect(screen.queryByRole('separator')).toBeNull();
  vi.restoreAllMocks();
 });
 it('opens the clicked evidence when a column contains multiple entries from the same document',async()=>{
  const p=payload();const c=p.rows[0].cells.LABEL!;c.items.push({...c.items[0],id:'second',page:3,bbox:{x0:150,y0:50,x1:220,y1:65},description:'Second label variant'});
  vi.mocked(api.quickView).mockResolvedValue(p);open();
  fireEvent.click(await screen.findByRole('button',{name:'Show Label source for row 1, entry 2'}));
  await waitFor(()=>expect(screen.getByTestId('LABEL.pdf, page 3').getAttribute('data-box')).toContain('150'));
 });
 it('shows all three matched sources in green and follows each actual evidence page',async()=>{
  vi.mocked(api.quickView).mockResolvedValue(payload());open();
  await screen.findByRole('button',{name:'SKU 1 SKU-A'});
  fireEvent.click(screen.getByRole('button',{name:'Show Label source for row 1'}));
  for(const [n,k] of kinds.entries()){
   const source=screen.getByRole('region',{name:`${names[n]} source preview`});
   await waitFor(()=>expect(within(source).getByTestId(`${k}.pdf, page ${n+1}`).getAttribute('data-tone')).toBe('matched'));
   expect(within(source).getByTestId(`${k}.pdf, page ${n+1}`).getAttribute('data-box')).toContain('20');
  }
  fireEvent.click(screen.getByText(/Comparison details/));
  expect(screen.getByRole('link',{name:/BOM ↔ Label/}).getAttribute('href')).toBe('/runs/run/rows/pair');
  fireEvent.click(screen.getByRole('button',{name:'Clear selection'}));
  expect(screen.getByTestId('BOM.pdf, page 1').getAttribute('data-box')).toBe('null');
 });
 it('keeps missing counterparts empty and highlights only the existing orange sources',async()=>{
  const p=payload();p.rows[0].status='attention';p.rows[0].cells={BOM:cell('BOM','attention'),LABEL:null,DRAWING:cell('DRAWING','attention')};p.rows[0].checks=[];
  vi.mocked(api.quickView).mockResolvedValue(p);open();
  fireEvent.click(await screen.findByRole('button',{name:'Show missing Label for row 1'}));
  expect(screen.getByTestId('BOM.pdf, page 1').getAttribute('data-tone')).toBe('attention');
  expect(screen.getByTestId('LABEL.pdf, page 1').getAttribute('data-box')).toBe('null');
  expect(screen.getByText('No counterpart in this comparison. There is no location to highlight.')).toBeTruthy();
 });
 it('switches SKU without showing the previous SKU selection or document highlights',async()=>{
  vi.mocked(api.quickView).mockImplementation(async(_r,q)=>{
   const p=payload();if(q.sku==='SKU-B'){p.sku='SKU-B';p.documents=p.documents.slice(0,1);p.rows=[];p.total=0;}return p;
  });open();
  fireEvent.click(await screen.findByRole('button',{name:'Show BOM source for row 1'}));
  fireEvent.click(screen.getByRole('button',{name:'SKU 2 SKU-B'}));
  await screen.findByText('No label document');
  expect(screen.queryByText('Recorded source pairing')).toBeNull();
  expect(screen.getByTestId('BOM.pdf, page 1').getAttribute('data-box')).toBe('null');
  expect(screen.queryByTestId('LABEL.pdf, page 2')).toBeNull();
 });
 it('offers full extracted text with an explicit source-order and saved-text limitation',async()=>{
  vi.mocked(api.quickView).mockImplementation(async(_r,q)=>{const p=payload();p.view=q.view||'components';p.documents[0].full_text=false;return p;});open();
  fireEvent.click(await screen.findByRole('button',{name:'All extracted text'}));
  await screen.findByText(/Listed in source order/);
  expect(screen.getByText(/full-page text was not retained/)).toBeTruthy();
  expect(screen.queryByRole('combobox',{name:'Comparison status'})).toBeNull();
 });
 it('sends search and status filters to the SKU-scoped endpoint',async()=>{
  vi.mocked(api.quickView).mockResolvedValue(payload());open();
  fireEvent.change(await screen.findByRole('combobox',{name:'Comparison status'}),{target:{value:'attention'}});
  await waitFor(()=>expect(api.quickView).toHaveBeenLastCalledWith('run',expect.objectContaining({status:'attention'})));
  fireEvent.change(screen.getByRole('textbox',{name:'Search comparison text'}),{target:{value:'CAP001'}});
  await waitFor(()=>expect(api.quickView).toHaveBeenLastCalledWith('run',expect.objectContaining({search:'CAP001'})));
 });
 it('preserves search focus and SKU controls while a filtered request is pending',async()=>{
  let finish:((value:QuickView)=>void)|undefined;
  vi.mocked(api.quickView).mockImplementation(async(_r,q)=>q.search ? new Promise<QuickView>(resolve=>{finish=resolve;}) : payload());open();
  const input=await screen.findByRole('textbox',{name:'Search comparison text'});input.focus();
  fireEvent.change(input,{target:{value:'pending'}});
  await screen.findByText('Loading entries…');
  expect(screen.getByRole('button',{name:'SKU 2 SKU-B'})).toBeTruthy();
  expect(document.activeElement).toBe(input);
  finish?.(payload());
  await screen.findByRole('button',{name:'Show BOM source for row 1'});
 });
 it('clamps malformed offsets and paginates rather than silently truncating',async()=>{
  vi.mocked(api.quickView).mockImplementation(async(_r,q)=>({...payload(),total:201,offset:q.offset||0}));open('/runs/run/quick-view?offset=Infinity');
  await screen.findByText('1–100 of 201');
  expect(api.quickView).toHaveBeenLastCalledWith('run',expect.objectContaining({offset:0}));
  fireEvent.click(screen.getByRole('button',{name:'Next quick view page'}));
  await waitFor(()=>expect(api.quickView).toHaveBeenLastCalledWith('run',expect.objectContaining({offset:100})));
 });
 it('provides retry on API errors and a useful empty-run state',async()=>{
  vi.mocked(api.quickView).mockRejectedValueOnce(new Error('Run not shared')).mockResolvedValueOnce({...payload(),sku:null,groups:[],rows:[],documents:[],total:0});open();
  await screen.findByText('Run not shared');
  fireEvent.click(screen.getByRole('button',{name:'Retry'}));
  await screen.findByText('No SKU sets in this run');
  expect(screen.getByRole('link',{name:'Open documents'})).toBeTruthy();
 });
});

it('only offers comparison export when the server grants export access',async()=>{
 const p=payload();p.can_export=true;
 vi.mocked(api.quickView).mockResolvedValue(p);open();
 expect(await screen.findByRole('button',{name:'Download Excel'})).toBeTruthy();
 p.can_export=false;
 fireEvent.click(screen.getByRole('button',{name:'Refresh'}));
 await waitFor(()=>expect(screen.queryByRole('button',{name:'Download Excel'})).toBeNull());
});
