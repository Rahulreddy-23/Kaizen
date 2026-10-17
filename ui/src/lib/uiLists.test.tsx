// @vitest-environment jsdom
import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { usePagedList } from "./pagination";
import { groupDocuments } from "./documentGroups";
import type { DocumentSummary, SkuGroup } from "../types";
afterEach(cleanup);

describe("list pagination",()=>{
  it("resets filters and clamps a shrinking list rather than displaying an empty later page",()=>{
    const items=Array.from({length:80},(_,i)=>i);
    const {result,rerender}=renderHook(({data,key})=>usePagedList(data,key),{initialProps:{data:items,key:"all"}});
    act(()=>result.current.setOffset(50));
    expect(result.current.rows[0]).toBe(50);
    rerender({data:items.slice(0,30),key:"all"});
    expect(result.current.offset).toBe(25);
    rerender({data:items.slice(0,5),key:"search"});
    expect(result.current.rows).toEqual([0,1,2,3,4]);
    expect(result.current.offset).toBe(0);
  });
  it("can reveal a linked action item on its actual page",()=>{
    const {result}=renderHook(()=>usePagedList(Array.from({length:100},(_,i)=>i),"target",25,50));
    expect(result.current.rows[0]).toBe(50);
  });
});

const doc=(id:string,type:DocumentSummary["doc_type"],sku:string,sha=id)=>({id,doc_type:type,sku,sha256:sha,file_name:`${id}.pdf`,file:id,parser:"test",parser_version:"1",header:{},items:1,warnings:[],pages:1}) as DocumentSummary;
const groups=[{sku:"700KIT",document_ids:["bom","label","drawing"]},{sku:"800KIT",document_ids:["other","drawing"]}] as SkuGroup[];
describe("source document grouping",()=>{
  it("uses actual run associations, keeps duplicates, and lists shared drawings once",()=>{
    const docs=[doc("bom","BOM","700KIT"),doc("label","LABEL","700"),doc("label-copy","LABEL","700","label"),doc("export","BOM","700KIT"),doc("other","BOM","800KIT"),doc("drawing","DRAWING","DWG700")];
    const result=groupDocuments(docs,groups);
    expect(result.find(group=>group.sku==="700KIT")?.docs.map(d=>d.id)).toEqual(["bom","export","label-copy","label"]);
    expect(result.find(group=>group.key==="shared")?.docs.map(d=>d.id)).toEqual(["drawing"]);
    expect(result.flatMap(group=>group.docs)).toHaveLength(docs.length);
  });
  it("finds a label by full kit SKU even when its own REF omits a suffix",()=>{
    const result=groupDocuments([doc("bom","BOM","700KIT"),doc("label","LABEL","700"),doc("drawing","DRAWING","DWG700")],groups,"700KIT");
    expect(result.flatMap(group=>group.docs).map(d=>d.id)).toContain("label");
  });
});
