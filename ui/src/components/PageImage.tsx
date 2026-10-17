import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import type { BBox } from "../types";
import { Skeleton } from "./ui";

interface Props {
  /** Page PNG URL, or null when the source has no page image (spreadsheet). */
  src: string | null;
  /** Evidence box in PDF points (72 dpi). A client-side outline is drawn over the server-rendered highlight. */
  bbox?: BBox | null;
  /** DPI the server rendered the page at (API default 110). */
  dpi?: number;
  alt: string;
  /** true = fit to container width; false = actual pixel size (scrollable). */
  fit?: boolean;
  /** Reading zoom relative to 96 CSS pixels per inch; independent of render DPI. */
  zoom?: number;
  /** Explicitly return to evidence after the reader has panned away. */
  focusToken?: number;
  /** Wide row boxes can start at their first column instead of their centre. */
  alignWideEvidence?: "center" | "start";
  /** Enable drag-to-pan and keyboard scrolling for document readers. */
  pan?: boolean;
  /** Controlled document zoom. Enables touch pinch and trackpad/Ctrl-wheel zoom. */
  onZoomChange?: (percent: number) => void;
  fallback?: ReactNode;
  maxHeight?: string;
  /** Comparison status; omitted keeps the ordinary evidence accent. */
  tone?: "matched" | "attention" | "neutral";
}

export function PageImage({ src, bbox, dpi = 110, alt, fit = true, zoom, focusToken, alignWideEvidence = "center", pan = false, onZoomChange, fallback, maxHeight = "70vh", tone }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [scale, setScale] = useState<number | null>(null);
  const [naturalWidth, setNaturalWidth] = useState(0);
  const panStart = useRef<{x:number;y:number;left:number;top:number} | null>(null);
  const pointers = useRef(new Map<number, {x:number;y:number}>());
  const pinch = useRef<{distance:number;zoom:number;x:number;y:number} | null>(null);
  const anchor = useRef<{x:number;y:number;pointX:number;pointY:number} | null>(null);
  const manuallyMoved = useRef(false);
  const gestureOptions = useRef({onZoomChange, dpi});
  gestureOptions.current = {onZoomChange, dpi};
  const bboxKey = bbox ? `${bbox.x0},${bbox.y0},${bbox.x1},${bbox.y1}` : "";

  useEffect(() => {
    setStatus("loading");
    setScale(null);
    setNaturalWidth(0);
    pointers.current.clear(); pinch.current = null; panStart.current = null; anchor.current = null;
  }, [src]);

  useEffect(() => {manuallyMoved.current = false;}, [src, bboxKey, focusToken]);

  const currentZoom = () => {
    const img = imgRef.current;
    return img?.naturalWidth ? img.clientWidth / img.naturalWidth * gestureOptions.current.dpi / 96 * 100 : 100;
  };
  const zoomAt = (percent: number, x: number, y: number, point?: {x:number;y:number}) => {
    const c = containerRef.current, img = imgRef.current;
    if (!c || !img?.clientWidth || !gestureOptions.current.onZoomChange) return;
    const bounds = c.getBoundingClientRect();
    const localX = x - bounds.left - c.clientLeft, localY = y - bounds.top - c.clientTop;
    anchor.current = {x:localX,y:localY,pointX:point?.x ?? (c.scrollLeft + localX) / img.clientWidth,pointY:point?.y ?? (c.scrollTop + localY) / img.clientWidth};
    manuallyMoved.current = true;
    gestureOptions.current.onZoomChange(Math.round(Math.min(400, Math.max(25, percent))));
  };
  // Preserve the point under the fingers/cursor, rather than snapping back to evidence.
  useLayoutEffect(() => {
    const c = containerRef.current, img = imgRef.current, target = anchor.current;
    if (!c || !img?.clientWidth || !target) return;
    c.scrollLeft = target.pointX * img.clientWidth - target.x;
    c.scrollTop = target.pointY * img.clientWidth - target.y;
    anchor.current = null;
  }, [zoom, fit, naturalWidth]);

  useEffect(() => {
    const c = containerRef.current;
    if (!c || !pan || !onZoomChange) return;
    const wheel = (event: WheelEvent) => {
      if (!event.ctrlKey || !imgRef.current?.clientWidth) return;
      event.preventDefault();
      const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? c.clientHeight : 1);
      zoomAt(currentZoom() * Math.exp(-Math.max(-100, Math.min(100, delta)) * .01), event.clientX, event.clientY);
    };
    c.addEventListener("wheel", wheel, {passive:false});
    return () => c.removeEventListener("wheel", wheel);
    // The handler reads current props through gestureOptions and the image geometry.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pan, !!onZoomChange, src]);

  // scale = rendered CSS px per PDF point: (clientWidth / naturalWidth) * (dpi / 72)
  const measure = useCallback(() => {
    const img = imgRef.current;
    if (!img || !img.naturalWidth || !img.clientWidth) return;
    setScale((img.clientWidth / img.naturalWidth) * (dpi / 72));
  }, [dpi]);

  useEffect(() => {
    const img = imgRef.current;
    if (!img || status !== "ok") return;
    measure();
    const ro = new ResizeObserver(() => measure());
    ro.observe(img);
    return () => ro.disconnect();
  }, [measure, status, fit, zoom]);

  // Scroll the container so the evidence box is centred (never scrolls the page itself).
  useEffect(() => {
    const c = containerRef.current;
    if (!c || status !== "ok" || !bbox || scale === null || manuallyMoved.current) return;
    const top = bbox.y0 * scale;
    const left = bbox.x0 * scale;
    const h = (bbox.y1 - bbox.y0) * scale;
    const w = (bbox.x1 - bbox.x0) * scale;
    c.scrollTo({ top: Math.max(0, top + h / 2 - c.clientHeight / 2), left: Math.max(0, alignWideEvidence === "start" && w > c.clientWidth ? left - 16 : left + w / 2 - c.clientWidth / 2) });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, scale, bboxKey, focusToken, alignWideEvidence]);

  if (!src) return <div className="rounded-md border border-line bg-surface-2/60 p-4">{fallback}</div>;

  return (
    <div ref={containerRef} className={`relative rounded-md border border-line bg-surface-2 overflow-auto ${pan ? "quick-pan-canvas" : ""}`} style={{ maxHeight, touchAction: pan && onZoomChange ? "none" : undefined }} tabIndex={pan ? 0 : undefined} role={pan ? "region" : undefined} aria-label={pan ? `${alt} page canvas` : undefined}
      onPointerDown={e => {
        if (!pan || (e.pointerType === "touch" ? !onZoomChange : e.button !== 0)) return;
        manuallyMoved.current = true;
        pointers.current.set(e.pointerId,{x:e.clientX,y:e.clientY});
        if (pointers.current.size === 2 && onZoomChange) {
          const [a,b] = [...pointers.current.values()], c = e.currentTarget, bounds = c.getBoundingClientRect(), width = imgRef.current?.clientWidth || 1;
          const x = (a.x+b.x)/2 - bounds.left-c.clientLeft, y = (a.y+b.y)/2-bounds.top-c.clientTop;
          pinch.current = {distance:Math.max(1,Math.hypot(a.x-b.x,a.y-b.y)),zoom:currentZoom(),x:(c.scrollLeft+x)/width,y:(c.scrollTop+y)/width};
          panStart.current = null;
        } else if (pointers.current.size === 1) {
        panStart.current={x:e.clientX,y:e.clientY,left:e.currentTarget.scrollLeft,top:e.currentTarget.scrollTop};
        }
        e.currentTarget.setPointerCapture?.(e.pointerId);e.preventDefault();
      }}
      onPointerMove={e => {
        if (!pointers.current.has(e.pointerId)) return;
        pointers.current.set(e.pointerId,{x:e.clientX,y:e.clientY});
        const gesture = pinch.current;
        if (gesture && pointers.current.size === 2) {
          const [a,b] = [...pointers.current.values()];
          zoomAt(gesture.zoom * Math.hypot(a.x-b.x,a.y-b.y)/gesture.distance,(a.x+b.x)/2,(a.y+b.y)/2,{x:gesture.x,y:gesture.y});
        } else {const start=panStart.current;if(start){e.currentTarget.scrollLeft=start.left + start.x-e.clientX;e.currentTarget.scrollTop=start.top + start.y-e.clientY;}}
      }}
      onPointerUp={e=>{
        pointers.current.delete(e.pointerId);pinch.current=null;panStart.current=null;
        const remaining=[...pointers.current.values()][0];
        if (remaining) panStart.current={...remaining,left:e.currentTarget.scrollLeft,top:e.currentTarget.scrollTop};
      }} onPointerCancel={()=>{pointers.current.clear();pinch.current=null;panStart.current=null;}} onLostPointerCapture={e=>{if(pointers.current.has(e.pointerId)){pointers.current.clear();pinch.current=null;panStart.current=null;}}}>
      {status === "loading" && (
        <div className="absolute inset-0 p-4 space-y-3" aria-hidden>
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-5/6" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-2/3" />
        </div>
      )}
      {status === "error" ? (
        <div className="p-4 text-sm">{fallback}</div>
      ) : (
        <div className={`relative ${fit ? "w-full" : "w-max"}`} style={!fit && zoom && naturalWidth ? {width: naturalWidth * (96 / dpi) * zoom / 100} : undefined}>
          <img
            ref={imgRef}
            src={src}
            alt={alt}
            draggable={pan ? false : undefined}
            className={`block h-auto transition-opacity duration-200 ease-out ${fit || zoom ? "w-full" : "max-w-none"} ${status === "ok" ? "opacity-100" : "opacity-0"}`}
            onLoad={() => {
              setNaturalWidth(imgRef.current?.naturalWidth ?? 0);
              setStatus("ok");
              measure();
            }}
            onError={() => setStatus("error")}
          />
          {bbox && scale !== null && status === "ok" && (
            <div
              className="absolute rounded-sm border-2 border-accent-500 pointer-events-none enter-pop"
              data-highlight-tone={tone ?? "default"}
              style={{
                borderColor: tone ? `rgb(var(--c-${tone === "matched" ? "ok-strong" : tone === "attention" ? "warn-strong" : "ink-3"}))` : undefined,
                backgroundColor: tone ? `rgb(var(--c-${tone === "matched" ? "ok" : tone === "attention" ? "warn" : "ink-3"}) / 0.12)` : undefined,
                left: bbox.x0 * scale - 4,
                top: bbox.y0 * scale - 4,
                width: (bbox.x1 - bbox.x0) * scale + 8,
                height: (bbox.y1 - bbox.y0) * scale + 8,
                boxShadow: "0 0 0 2px rgba(255,255,255,0.9), 0 0 0 9999px rgba(15,31,53,0.06)",
              }}
            />
          )}
        </div>
      )}
    </div>
  );
}
