// @vitest-environment jsdom
import {cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, expect, it, vi} from "vitest";
import {PageImage} from "./PageImage";

afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});

it('pans the reading canvas with a captured pointer and stops on release',()=>{
  vi.stubGlobal('PointerEvent',MouseEvent);
  render(<PageImage src="/page.png" alt="Source" pan/>);
  const canvas=screen.getByRole('region',{name:'Source page canvas'});
  canvas.scrollLeft=60;canvas.scrollTop=50;
  fireEvent.pointerDown(canvas,{button:0,clientX:100,clientY:100});
  fireEvent.pointerMove(canvas,{clientX:70,clientY:80});
  expect(canvas.scrollLeft).toBe(90);expect(canvas.scrollTop).toBe(70);
  fireEvent.pointerUp(canvas);
  fireEvent.pointerMove(canvas,{clientX:10,clientY:10});
  expect(canvas.scrollLeft).toBe(90);expect(canvas.scrollTop).toBe(70);
});

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

function gestureCanvas() {
  class TestPointer extends MouseEvent {
    pointerId:number;pointerType:string;
    constructor(type:string, options:MouseEventInit & {pointerId?:number;pointerType?:string}={}) {super(type,options);this.pointerId=options.pointerId ?? 1;this.pointerType=options.pointerType ?? 'touch';}
  }
  vi.stubGlobal('PointerEvent',TestPointer);
  vi.stubGlobal('ResizeObserver',class {observe(){}disconnect(){}});
  vi.spyOn(HTMLImageElement.prototype,'naturalWidth','get').mockReturnValue(1500);
  vi.spyOn(HTMLImageElement.prototype,'clientWidth','get').mockImplementation(function(this:HTMLImageElement){return parseFloat(this.parentElement?.style.width || '600');});
  const onZoom=vi.fn();
  const props={src:'/page.png',alt:'Source',pan:true,dpi:180,fit:false,zoom:100,onZoomChange:onZoom};
  const view=render(<PageImage {...props}/>);
  const canvas=screen.getByRole('region',{name:'Source page canvas'});
  fireEvent.load(screen.getByAltText('Source'));
  canvas.scrollLeft=200;canvas.scrollTop=100;
  return {canvas,onZoom,view,props};
}

it('pinches around the midpoint, continues one-finger panning, and cancels cleanly',()=>{
  const {canvas,onZoom,view,props}=gestureCanvas();
  fireEvent.pointerDown(canvas,{pointerId:1,pointerType:'touch',clientX:100,clientY:100});
  fireEvent.pointerDown(canvas,{pointerId:2,pointerType:'touch',clientX:200,clientY:100});
  fireEvent.pointerMove(canvas,{pointerId:2,pointerType:'touch',clientX:300,clientY:100});
  expect(onZoom).toHaveBeenLastCalledWith(200);
  view.rerender(<PageImage {...props} zoom={200}/>);
  expect(canvas.scrollLeft).toBeCloseTo(500);expect(canvas.scrollTop).toBeCloseTo(300);
  fireEvent.pointerUp(canvas,{pointerId:2});
  fireEvent.lostPointerCapture(canvas,{pointerId:2});
  fireEvent.pointerMove(canvas,{pointerId:1,clientX:80,clientY:90});
  expect(canvas.scrollLeft).toBeCloseTo(520);expect(canvas.scrollTop).toBeCloseTo(310);
  fireEvent.pointerCancel(canvas,{pointerId:1});
  fireEvent.pointerMove(canvas,{pointerId:1,clientX:0,clientY:0});
  expect(canvas.scrollLeft).toBeCloseTo(520);
});

it('zooms out when fingers come together and clamps the reading scale',()=>{
  const {canvas,onZoom}=gestureCanvas();
  fireEvent.pointerDown(canvas,{pointerId:1,clientX:0,clientY:0});
  fireEvent.pointerDown(canvas,{pointerId:2,clientX:100,clientY:0});
  fireEvent.pointerMove(canvas,{pointerId:2,clientX:50,clientY:0});
  expect(onZoom).toHaveBeenLastCalledWith(50);
  fireEvent.pointerMove(canvas,{pointerId:2,clientX:5,clientY:0});expect(onZoom).toHaveBeenLastCalledWith(25);
  fireEvent.pointerMove(canvas,{pointerId:2,clientX:1000,clientY:0});expect(onZoom).toHaveBeenLastCalledWith(400);
});

it('intercepts Ctrl-wheel zoom only inside an enabled canvas and preserves the cursor point',()=>{
  const {canvas,onZoom,view,props}=gestureCanvas();
  const ordinary=new WheelEvent('wheel',{deltaY:40,bubbles:true,cancelable:true});canvas.dispatchEvent(ordinary);
  expect(ordinary.defaultPrevented).toBe(false);expect(onZoom).not.toHaveBeenCalled();
  const wheel=new WheelEvent('wheel',{ctrlKey:true,deltaY:-Math.log(2)*100,clientX:100,clientY:100,bubbles:true,cancelable:true});
  canvas.dispatchEvent(wheel);expect(wheel.defaultPrevented).toBe(true);expect(onZoom).toHaveBeenCalledWith(200);
  view.rerender(<PageImage {...props} zoom={200}/>);
  expect(canvas.scrollLeft).toBeCloseTo(500);expect(canvas.scrollTop).toBeCloseTo(300);
  view.rerender(<PageImage {...props} onZoomChange={undefined}/>);
  const legacy=new WheelEvent('wheel',{ctrlKey:true,deltaY:40,bubbles:true,cancelable:true});canvas.dispatchEvent(legacy);
  expect(legacy.defaultPrevented).toBe(false);
});

it('does not snap a gestured page back to its highlight until Locate is requested',async()=>{
  const {canvas,view,props}=gestureCanvas();
  const scroll=vi.fn();Object.defineProperty(canvas,'scrollTo',{configurable:true,value:scroll});
  const box={x0:20,y0:30,x1:100,y1:42};
  view.rerender(<PageImage {...props} bbox={box} focusToken={1}/>);
  await waitFor(()=>expect(scroll).toHaveBeenCalled());scroll.mockClear();
  fireEvent.wheel(canvas,{ctrlKey:true,deltaY:-20,clientX:100,clientY:100});
  view.rerender(<PageImage {...props} bbox={box} focusToken={1} zoom={150}/>);
  expect(scroll).not.toHaveBeenCalled();
  view.rerender(<PageImage {...props} bbox={box} focusToken={2} zoom={150}/>);
  await waitFor(()=>expect(scroll).toHaveBeenCalled());
});
