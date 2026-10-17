// @vitest-environment jsdom
import {cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";
import {PageImage} from "./PageImage";

afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});

it('keeps PDF-point highlights aligned at reading zoom independently of render DPI', async()=>{
  vi.stubGlobal('ResizeObserver', class { constructor(private cb:()=>void) {} observe(){this.cb();} disconnect(){} });
  vi.spyOn(HTMLImageElement.prototype,'naturalWidth','get').mockReturnValue(1500);
  vi.spyOn(HTMLImageElement.prototype,'clientWidth','get').mockImplementation(function(this:HTMLImageElement){return parseFloat(this.parentElement?.style.width || '500');});
  const scroll=vi.fn();Object.defineProperty(HTMLElement.prototype,'scrollTo',{configurable:true,value:scroll});
  const box={x0:20,y0:30,x1:100,y1:42};
  const {container,rerender}=render(<PageImage src="/page.png" bbox={box} dpi={180} zoom={125} fit={false} alt="Source" tone="matched"/>);
  fireEvent.load(screen.getByAltText('Source'));
  await waitFor(()=>expect(screen.getByAltText('Source').parentElement?.style.width).toBe('1000px'));
  await waitFor(()=>expect(parseFloat((container.querySelector('[data-highlight-tone]') as HTMLElement).style.left)).toBeCloseTo(20 * 96/72 * 1.25 - 4));
  expect(scroll).toHaveBeenCalled();
  rerender(<PageImage src="/page.png" bbox={box} dpi={180} zoom={200} fit={false} alt="Source" tone="attention"/>);
  await waitFor(()=>expect(parseFloat((container.querySelector('[data-highlight-tone]') as HTMLElement).style.left)).toBeCloseTo(20 * 96/72 * 2 - 4));
  expect(container.querySelector('[data-highlight-tone="attention"]')).toBeTruthy();
});
