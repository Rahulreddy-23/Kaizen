// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { addFileSet, addFolders, folderProblem, MAX_RUN_BYTES, supportedRunFiles, uploadProblem, type UploadFolder } from "./uploads";

const inFolder = (path: string, size = 4) => {
  const file = new File(["x".repeat(size)], path.split("/").pop()!, { lastModified: 1 });
  Object.defineProperty(file, "webkitRelativePath", { value: path });
  return file;
};
const three = (dir: string) => ["a.pdf", "b.pdf", "c.xlsx"].map(name => inFolder(`${dir}/${name}`));

describe("upload selection", () => {
  it("keeps supported documents and excludes lock files and unrelated folder contents", () => {
    const files = ["bom.PDF", "label.pdf", "pco.xlsm", "export.csv", "~$bom.xlsx", ".hidden.pdf", "notes.txt"].map(name => new File(["data"], name));
    expect(supportedRunFiles(files).map(file => file.name)).toEqual(["bom.PDF", "label.pdf", "pco.xlsm", "export.csv"]);
  });
  it("groups a folder pick by directory, whatever the names", () => {
    const folders = addFolders([], [...three("Anything/x"), ...three("Anything/y"), inFolder("Anything/notes.txt")]);
    expect(folders.map(f => [f.name, f.files.length])).toEqual([["Anything/x", 3], ["Anything/y", 3]]);
  });
  it("keeps same-named folders apart and ignores the same folder picked twice", () => {
    const first = addFolders([], three("Kit"));
    const again = addFolders(first, three("Kit"));
    expect(again).toHaveLength(1);
    const other = addFolders(first, [inFolder("Kit/a.pdf", 9), inFolder("Kit/b.pdf"), inFolder("Kit/c.pdf")]);
    expect(other.map(f => f.name)).toEqual(["Kit", "Kit (2)"]);
  });
  it("recognises a folder picked through its parent and then on its own", () => {
    const viaParent = addFolders([], [...three("Batch/Kit"), ...three("Batch/Other")]);
    expect(addFolders(viaParent, three("Kit")).map(f => f.name)).toEqual(["Batch/Kit", "Batch/Other"]);
  });
  it("adds exactly three files chosen together as one run", () => {
    const loose = () => ["one.pdf", "two.pdf", "three.csv"].map(name => new File(["x"], name, { lastModified: 1 }));
    const first = addFileSet([], loose());
    expect(first.problem).toBeNull();
    expect(first.folders).toEqual([{ name: "Selected files", files: expect.any(Array), loose: true }]);
    expect(addFileSet(first.folders, loose()).problem).toContain("already added");
    const other = addFileSet(first.folders, ["a.pdf", "b.pdf", "c.pdf"].map(name => new File(["x"], name)));
    expect(other.folders.map(f => f.name)).toEqual(["Selected files", "Selected files (2)"]);
    for (const count of [1, 2, 4]) {
      const result = addFileSet([], Array.from({ length: count }, (_, i) => new File(["x"], `${i}.pdf`)));
      expect(result.problem).toContain(`You selected ${count}`);
      expect(result.folders).toEqual([]);
    }
    expect(addFileSet([], [...loose().slice(0, 2), new File(["x"], "notes.txt")]).problem).toContain("You selected 2");
  });
  it("requires exactly three documents inside a folder", () => {
    expect(folderProblem({ name: "Kit", files: three("Kit") })).toBeNull();
    expect(folderProblem({ name: "Kit", files: three("Kit").slice(0, 2) })).toContain("needs exactly 3");
    expect(folderProblem({ name: "", files: three("") })).toContain("not inside a folder");
  });
  it("refuses empty, incomplete and oversized selections before sending a request", () => {
    expect(uploadProblem([])).toContain("Choose a folder");
    expect(uploadProblem([{ name: "Kit", files: three("Kit").slice(0, 1) }])).toContain("Folder 'Kit'");
    const big = (size: number): UploadFolder[] => [{ name: "Kit", files: [{ size } as File, { size: 0 } as File, { size: 0 } as File] }];
    expect(uploadProblem(big(MAX_RUN_BYTES + 1))).toContain("250 MB");
    expect(uploadProblem([...big(MAX_RUN_BYTES), { ...big(MAX_RUN_BYTES)[0], name: "Kit 2" }])).toBeNull();  // the limit is per run, and each folder is a run
  });
});

it('keeps separate identical same-named sibling kits within one parent selection', () => {
  expect(addFolders([], [...three('Batch/First/Kit'), ...three('Batch/Second/Kit')]).map(f => f.name)).toEqual(['Batch/First/Kit', 'Batch/Second/Kit']);
});

it('rejects loose files with colliding upload paths', () => {
  expect(addFileSet([], [new File(['a'], 'doc.pdf'), new File(['b'], 'doc.pdf'), new File(['c'], 'bom.xlsx')]).problem).toContain('duplicate names');
});
