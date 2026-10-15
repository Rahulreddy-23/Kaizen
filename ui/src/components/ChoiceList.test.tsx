// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { ChoiceList } from "./ChoiceList";

afterEach(cleanup);
const options = [{value:"needle",label:"Safety needle",description:"Item 123 · Page 2"}, {value:"holder",label:"Needle holder"}, {value:"tape",label:"Measuring tape"}];
function List({disabled=false}: {disabled?: boolean}) {
  const [value,setValue]=useState(["needle"]);
  return <ChoiceList label="Source components" options={options} value={value} onChange={setValue} disabled={disabled} hint="Verify against the source." />;
}
describe("searchable checkbox lists", () => {
  it("preserves selections when searching, supports multiple choices and clears explicitly", () => {
    render(<List />);
    fireEvent.change(screen.getByRole("searchbox"), {target:{value:"holder"}});
    expect(screen.queryByRole("checkbox",{name:/Safety needle/})).toBeNull();
    fireEvent.click(screen.getByRole("checkbox",{name:"Needle holder"}));
    expect(screen.getByText("2 selected")).toBeTruthy();
    const selected=screen.getByRole("list",{name:"Selected source components"});
    expect(within(selected).getByText("Safety needle")).toBeTruthy();
    fireEvent.change(screen.getByRole("searchbox"),{target:{value:""}});
    expect((screen.getByRole("checkbox",{name:/Safety needle/}) as HTMLInputElement).checked).toBe(true);
    fireEvent.click(screen.getByRole("button",{name:"Clear source components"}));
    expect(screen.getByText("None selected")).toBeTruthy();
    expect(screen.getAllByRole("checkbox").every(input=>!(input as HTMLInputElement).checked)).toBe(true);
  });
  it("keeps selected items removable when no search result matches",()=>{
    render(<List />);
    fireEvent.change(screen.getByRole("searchbox"),{target:{value:"unmatched"}});
    expect(screen.getByText(/Your selections are kept/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button",{name:"Remove Safety needle from source components"}));
    expect(screen.getByText("None selected")).toBeTruthy();
  });
  it("exposes the fieldset label, help and read-only state without modifier-key gestures",()=>{
    render(<List disabled />);
    const group=screen.getByRole("group",{name:"Source components"}) as HTMLFieldSetElement;
    expect(group.disabled).toBe(true);
    expect(group.getAttribute("aria-describedby")).toBeTruthy();
    expect(screen.queryByRole("listbox")).toBeNull();
  });
});
