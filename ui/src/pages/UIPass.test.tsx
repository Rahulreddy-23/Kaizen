// @vitest-environment jsdom
import {cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import {MemoryRouter, Route, Routes} from "react-router-dom";
import {api} from "../api";
import {ScreenBoundary} from "../components/ScreenBoundary";
import DocumentPage from "./DocumentPage";
import DocumentsPage from "./DocumentsPage";
import TerminologyPage from "./TerminologyPage";

vi.mock("../api",()=>({api:{getDocumentItems:vi.fn(),getDocuments:vi.fn(),getRun:vi.fn(),pageImageUrl:vi.fn(),annotatedBomUrl:vi.fn(),terminology:{list:vi.fn(),get:vi.fn(),history:vi.fn()}}}));
vi.mock("../lib/reviewer",()=>({useReviewer:()=>({name:"viewer@bd.com",session:{is_admin:false}})}));
vi.mock("../lib/toast",()=>({useToast:()=>vi.fn()}));
vi.mock("../components/PageImage",()=>({PageImage:({src,alt}:{src:string;alt:string})=><img src={src} alt={alt} />}));
afterEach(()=>{cleanup();vi.restoreAllMocks();});
beforeEach(()=>vi.clearAllMocks());

describe("document source controls",()=>{
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
  expect(api.annotatedBomUrl).not.toHaveBeenCalled();
 });
});

it("keeps ordinary reviewers out of administrator-only terminology forms",async()=>{
 vi.mocked(api.terminology.list).mockResolvedValue([{id:"REL-001",canonical:"Cap",aliases:["End cap"],scope:"global",doc_types:[],item_anchors:[],active:true,version:1,provenance:"manual",created_by:"admin@bd.com",created_at:"2026-01-01",updated_at:"2026-01-01",notes:"Verified wording"}]);
 vi.mocked(api.terminology.get).mockResolvedValue({id:"REL-001",canonical:"Cap",aliases:["End cap"],scope:"global",doc_types:[],item_anchors:[],active:true,version:1,provenance:"manual",created_by:"admin@bd.com",created_at:"2026-01-01",updated_at:"2026-01-01",notes:"Verified wording"});
 vi.mocked(api.terminology.history).mockResolvedValue([]);
 render(<MemoryRouter><TerminologyPage /></MemoryRouter>);
 expect((screen.getByRole("button",{name:"New relationship"}) as HTMLButtonElement).disabled).toBe(true);
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
