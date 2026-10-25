// @vitest-environment jsdom
import {cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {MemoryRouter, Route, Routes} from "react-router-dom";
import {api} from "../api";
import {ScreenBoundary} from "../components/ScreenBoundary";
import DocumentPage from "./DocumentPage";
import DocumentsPage from "./DocumentsPage";
import TerminologyPage from "./TerminologyPage";

vi.mock("../api",()=>({api:{getDocumentItems:vi.fn(),getDocuments:vi.fn(),getRun:vi.fn(),pageImageUrl:vi.fn(),annotatedUrl:vi.fn(),terminology:{list:vi.fn(),get:vi.fn(),history:vi.fn()}}}));
vi.mock("../lib/reviewer",()=>({useReviewer:()=>({name:"viewer@bd.com",session:{is_admin:false}})}));
vi.mock("../lib/toast",()=>({useToast:()=>vi.fn()}));
vi.mock("../components/PageImage",()=>({PageImage:({src,alt}:{src:string;alt:string})=><img src={src} alt={alt} />}));
afterEach(()=>{cleanup();vi.restoreAllMocks();});
beforeEach(()=>vi.clearAllMocks());

describe("document source controls",()=>{
 it("expands a category explanation without selecting the source row",async()=>{
  vi.mocked(api.getDocumentItems).mockResolvedValue({doc_id:"doc",doc_type:"BOM",file_name:"bom.xlsx",pages:0,header:{},warnings:[],items:[{id:"item",doc_id:"doc",doc_type:"BOM",file:"bom.xlsx",file_name:"bom.xlsx",sha256:"abc",page:null,bbox:null,locator:"row 1",raw_text:"Cap",sheet:"BOM",item_number:"CAP001",description:"Cap",quantity:"1",uom:"EA",oper_seq:"1",category:"PHYSICAL_COMPONENT",category_reason:"A physical component with positive quantity.",confidence:1,attributes:{},sub_quantity:null,is_active:true}]});
  render(<MemoryRouter initialEntries={["/runs/run/documents/doc"]}><Routes><Route path="/runs/:runId/documents/:docId" element={<DocumentPage />} /></Routes></MemoryRouter>);
  const explanation=await screen.findByText("Why this category");
  const details=explanation.closest("details")!;
  expect(details.open).toBe(false);
  fireEvent.click(explanation);
  expect(details.open).toBe(true);
  expect(screen.getByRole("button",{name:"View extracted line 1"}).getAttribute("aria-pressed")).toBe("false");
  expect(screen.getByText("A physical component with positive quantity.")).toBeTruthy();
 });
 it.each([["999",3],["-8",1],["Infinity",1],["2.8",2]])("clamps page=%s to an actual source page",async(query,page)=>{
  vi.mocked(api.getDocumentItems).mockResolvedValue({doc_id:"doc",doc_type:"BOM",file_name:"bom.pdf",pages:3,header:{},warnings:[],items:[]});
  vi.mocked(api.pageImageUrl).mockImplementation((_run,_doc,p)=>`/pages/${p}`);
  render(<MemoryRouter initialEntries={[`/runs/run/documents/doc?page=${query}`]}><Routes><Route path="/runs/:runId/documents/:docId" element={<DocumentPage />} /></Routes></MemoryRouter>);
  const control=await screen.findByRole("combobox",{name:"Page"});
  expect((control as HTMLSelectElement).value).toBe(String(page));
  expect((screen.getByRole("img") as HTMLImageElement).getAttribute("src")).toBe(`/pages/${page}`);
 });
 it("does not offer annotated-PDF download for a spreadsheet BOM",async()=>{
  vi.mocked(api.getRun).mockResolvedValue({permission:"owner",groups:[]} as never);
  vi.mocked(api.getDocuments).mockResolvedValue([{id:"sheet",doc_type:"BOM",file_name:"bom.xlsx",file:"bom.xlsx",sku:"700KIT",parser:"table",parser_version:"1",sha256:"abc",items:2,pages:0,warnings:[],header:{}}]);
  render(<MemoryRouter initialEntries={["/runs/run/documents"]}><Routes><Route path="/runs/:runId/documents" element={<DocumentsPage />} /></Routes></MemoryRouter>);
  await screen.findByRole("link",{name:"bom.xlsx"});
  expect(screen.queryByRole("link",{name:"Annotated BOM"})).toBeNull();
  expect(api.annotatedUrl).not.toHaveBeenCalled();
 });
});

it("allows reviewers to approve terms while keeping shared edits and imports administrator-only",async()=>{
 vi.mocked(api.terminology.list).mockResolvedValue([{id:"REL-001",canonical:"Cap",aliases:["End cap"],scope:"global",doc_types:[],item_anchors:[],active:true,version:1,provenance:"manual",created_by:"admin@bd.com",created_at:"2026-01-01",updated_at:"2026-01-01",notes:"Verified wording"}]);
 vi.mocked(api.terminology.get).mockResolvedValue({id:"REL-001",canonical:"Cap",aliases:["End cap"],scope:"global",doc_types:[],item_anchors:[],active:true,version:1,provenance:"manual",created_by:"admin@bd.com",created_at:"2026-01-01",updated_at:"2026-01-01",notes:"Verified wording"});
 vi.mocked(api.terminology.history).mockResolvedValue([]);
 render(<MemoryRouter><TerminologyPage /></MemoryRouter>);
 expect((screen.getByRole("button",{name:"Approve relationship"}) as HTMLButtonElement).disabled).toBe(false);
 expect(screen.queryByLabelText("File to import")).toBeNull();
 fireEvent.click(await screen.findByRole("button",{name:/Open relationship REL-001/}));
 await screen.findByText("Verified wording");
 expect(screen.queryByRole("button",{name:"Save new version"})).toBeNull();
 expect(screen.queryByRole("button",{name:"Deactivate"})).toBeNull();
});

it("keeps a recovery action available when a screen throws",async()=>{
 vi.spyOn(console,"error").mockImplementation(()=>{});
 function Broken():never {throw new Error("Synthetic render failure");}
 render(<MemoryRouter><ScreenBoundary><Broken /></ScreenBoundary></MemoryRouter>);
 await waitFor(()=>expect(screen.getByRole("alert")).toBeTruthy());
 expect(screen.getByRole("button",{name:"Reload page"})).toBeTruthy();
 expect(screen.getByRole("link",{name:"All runs"}).getAttribute("href")).toBe("/");
});

describe('full source text coverage', () => {
 const entry = (id: string, description: string, page = 1) => ({id,doc_id:'doc',doc_type:'DRAWING' as const,file:'drawing.pdf',file_name:'drawing.pdf',sha256:'abc',page,bbox:{x0:20,y0:30,x1:250,y1:42},locator:`page ${page}`,raw_text:description,sheet:null,item_number:null,description,quantity:null,uom:null,oper_seq:null,category:'DOCUMENT',category_reason:'Source text',confidence:.91,attributes:{},sub_quantity:null,is_active:true});
 const open = () => render(<MemoryRouter initialEntries={['/runs/run/documents/doc']}><Routes><Route path='/runs/:runId/documents/:docId' element={<DocumentPage />} /></Routes></MemoryRouter>);
 it('displays recovered spaces while keeping the original OCR available in the selected source',async()=>{
  const line={...entry('text','2 Each - Protective Cover'),raw_text:'2Each-ProtectiveCover'};
  vi.mocked(api.getDocumentItems).mockResolvedValue({doc_id:'doc',doc_type:'LABEL',file_name:'label.pdf',pages:1,header:{},warnings:[],items:[],text_lines:[line]});
  open();
  fireEvent.click(await screen.findByRole('button',{name:'All recognized text'}));
  expect(screen.getByText('2 Each - Protective Cover')).toBeTruthy();
  expect(screen.queryByText('2Each-ProtectiveCover')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'View extracted line 1'}));
  expect(screen.getByText('2Each-ProtectiveCover')).toBeTruthy();
 });
 it('shows retained notes separately, filters them and opens their actual source page', async () => {
  vi.mocked(api.getDocumentItems).mockResolvedValue({doc_id:'doc',doc_type:'DRAWING',file_name:'drawing.pdf',pages:2,header:{notes:[{page:2,text:'Verify the outer barrier'}]},warnings:[],items:[entry('component','Protective cover')],text_lines:[entry('text','Verify the outer barrier before shipping',2)]});
  vi.mocked(api.pageImageUrl).mockImplementation((_run,_doc,p)=>`/pages/${p}`);
  open();
  await screen.findByText('Protective cover');
  expect(screen.queryByText('Verify the outer barrier before shipping')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'All recognized text'}));
  await screen.findByText('Verify the outer barrier before shipping');
  fireEvent.change(screen.getByRole('textbox',{name:/Filter extracted lines/}),{target:{value:'outer barrier'}});
  fireEvent.click(screen.getByRole('button',{name:'View extracted line 1'}));
  await waitFor(()=>expect((screen.getByRole('combobox',{name:'Page'}) as HTMLSelectElement).value).toBe('2'));
  expect((screen.getByRole('img') as HTMLImageElement).getAttribute('src')).toBe('/pages/2');
  expect(screen.queryByText('[object Object]')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Comparison entries'}));
  fireEvent.change(screen.getByRole('textbox',{name:/Filter extracted lines/}),{target:{value:''}});
  expect(screen.getByText('Protective cover')).toBeTruthy();
 });
 it('explains that older runs need a new upload to retain all text',async()=>{
  vi.mocked(api.getDocumentItems).mockResolvedValue({doc_id:'doc',doc_type:'LABEL',file_name:'label.pdf',pages:1,header:{},warnings:[],items:[]});
  open();
  fireEvent.click(await screen.findByRole('button',{name:'All recognized text'}));
  expect(screen.getByText('Full text is unavailable in this saved run')).toBeTruthy();
  expect(screen.getByText(/Existing reviews stay unchanged/)).toBeTruthy();
 });
 it('paginates long source text and resets pagination after a filter',async()=>{
  vi.mocked(api.getDocumentItems).mockResolvedValue({doc_id:'doc',doc_type:'DRAWING',file_name:'drawing.pdf',pages:2,header:{},warnings:[],items:[],text_lines:Array.from({length:105},(_,n)=>entry(`t${n}`,`Source sentence ${n+1}`))});
  open();
  fireEvent.click(await screen.findByRole('button',{name:'All recognized text'}));
  expect(screen.queryByText('Source sentence 105')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Next extracted lines page'}));
  expect(screen.getByText('Source sentence 105')).toBeTruthy();
  fireEvent.change(screen.getByRole('textbox',{name:/Filter extracted lines/}),{target:{value:'sentence 105'}});
  expect(screen.getByText('Source sentence 105')).toBeTruthy();
  expect(screen.queryByRole('button',{name:'Next extracted lines page'})).toBeNull();
 });
});
