// The theme module is the only place that decides which theme is on. Pure functions with injected
// storage and root, so the rules are testable without a browser.
import { describe, expect, it } from "vitest";
import { THEME_COLOR, THEME_KEY, applyTheme, readChoice, resolveTheme, toggleTheme, type ThemeDocument, type ThemeRoot, type ThemeStorage } from "./theme";

function fakeStorage(initial: Record<string, string> = {}): ThemeStorage & { dump: () => Record<string, string> } {
  const m = new Map(Object.entries(initial));
  return {
    getItem: (k) => m.get(k) ?? null,
    setItem: (k, v) => {
      m.set(k, v);
    },
    dump: () => Object.fromEntries(m),
  };
}

function throwingStorage(): ThemeStorage {
  return {
    getItem: () => {
      throw new Error("blocked");
    },
    setItem: () => {
      throw new Error("blocked");
    },
  };
}

function fakeRoot(): ThemeRoot {
  return { dataset: {}, style: { colorScheme: "" } };
}

function fakeDocument(): ThemeDocument & { meta: { content: string } } {
  const meta = { content: "" };
  return { meta, querySelector: (sel) => (sel === 'meta[name="theme-color"]' ? meta : null) };
}

describe("resolveTheme", () => {
  it("follows the system when the choice is system", () => {
    expect(resolveTheme("system", true)).toBe("dark");
    expect(resolveTheme("system", false)).toBe("light");
  });
  it("lets an explicit choice win over the system", () => {
    expect(resolveTheme("light", true)).toBe("light");
    expect(resolveTheme("dark", false)).toBe("dark");
  });
});

describe("readChoice", () => {
  it("is system when nothing is stored", () => {
    expect(readChoice(fakeStorage())).toBe("system");
  });
  it("returns a stored light or dark choice", () => {
    expect(readChoice(fakeStorage({ [THEME_KEY]: "dark" }))).toBe("dark");
    expect(readChoice(fakeStorage({ [THEME_KEY]: "light" }))).toBe("light");
  });
  it("treats an unknown stored value as system", () => {
    expect(readChoice(fakeStorage({ [THEME_KEY]: "banana" }))).toBe("system");
  });
  it("is system when storage is unavailable", () => {
    expect(readChoice(throwingStorage())).toBe("system");
  });
});

describe("applyTheme", () => {
  it("stamps the root and the browser chrome colour", () => {
    const root = fakeRoot();
    const doc = fakeDocument();
    applyTheme("dark", root, doc);
    expect(root.dataset.theme).toBe("dark");
    expect(root.style.colorScheme).toBe("dark");
    expect(doc.meta.content).toBe(THEME_COLOR.dark);
    applyTheme("light", root, doc);
    expect(root.dataset.theme).toBe("light");
    expect(root.style.colorScheme).toBe("light");
    expect(doc.meta.content).toBe(THEME_COLOR.light);
  });
  it("copes with a document that has no theme-color meta", () => {
    const root = fakeRoot();
    expect(() => applyTheme("dark", root, { querySelector: () => null })).not.toThrow();
    expect(root.dataset.theme).toBe("dark");
  });
});

describe("toggleTheme", () => {
  it("switches light to dark, applies it and remembers it", () => {
    const storage = fakeStorage();
    const root = fakeRoot();
    expect(toggleTheme("light", storage, root, fakeDocument())).toBe("dark");
    expect(root.dataset.theme).toBe("dark");
    expect(storage.dump()).toEqual({ [THEME_KEY]: "dark" });
  });
  it("switches dark back to light", () => {
    const storage = fakeStorage({ [THEME_KEY]: "dark" });
    const root = fakeRoot();
    expect(toggleTheme("dark", storage, root, fakeDocument())).toBe("light");
    expect(root.dataset.theme).toBe("light");
    expect(storage.dump()).toEqual({ [THEME_KEY]: "light" });
  });
  it("still switches when the choice cannot be stored", () => {
    const root = fakeRoot();
    expect(toggleTheme("light", throwingStorage(), root, fakeDocument())).toBe("dark");
    expect(root.dataset.theme).toBe("dark");
  });
});
