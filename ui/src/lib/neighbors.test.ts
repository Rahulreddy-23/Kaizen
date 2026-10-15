import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { loadNeighbors } from "./neighbors";
import type { ResultRow } from "../types";
vi.mock("../api",()=>({api:{getResults:vi.fn()}}));
beforeEach(()=>vi.clearAllMocks());
function source(total:number) {
  vi.mocked(api.getResults).mockImplementation(async (_run,query={})=>({total,offset:query.offset??0,limit:query.limit??100,
    rows:Array.from({length:Math.max(0,Math.min(query.limit??100,total-(query.offset??0)))},(_,index)=>({row_id:`r${index+(query.offset??0)}`} as ResultRow))}));
}
describe("evidence navigation",()=>{
  it("locates a direct link beyond the first queue page and retains filters",async()=>{
    source(350);
    expect(await loadNeighbors("run","r250",{offset:0,limit:100,sku:"ANY-KIT",needs_validation:true})).toEqual({prev:{id:"r249",offset:200},next:{id:"r251",offset:200},index:251,total:350});
    expect(vi.mocked(api.getResults).mock.calls.every(([,query])=>query?.sku==="ANY-KIT"&&query.needs_validation)).toBe(true);
  });
  it("navigates a page boundary without losing the previous page",async()=>{
    source(250);
    const result=await loadNeighbors("run","r100",{offset:100,limit:100});
    expect(result.prev).toEqual({id:"r99",offset:0});
    expect(result.next).toEqual({id:"r101",offset:100});
  });
  it("reports a row outside the filter without manufacturing neighbors",async()=>{
    source(140);
    expect(await loadNeighbors("run","absent",{offset:0,limit:100})).toEqual({prev:null,next:null,index:null,total:140});
  });
});
