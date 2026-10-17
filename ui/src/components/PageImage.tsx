import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
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
  fallback?: ReactNode;
  maxHeight?: string;
  /** Comparison status; omitted keeps the ordinary evidence accent. */
  tone?: "matched" | "attention" | "neutral";
}

export function PageImage({ src, bbox, dpi = 110, alt, fit = true, zoom, fallback, maxHeight = "70vh", tone }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const [scale, setScale] = useState<number | null>(null);
  const [naturalWidth, setNaturalWidth] = useState(0);
  const bboxKey = bbox ? `${bbox.x0},${bbox.y0},${bbox.x1},${bbox.y1}` : "";

  useEffect(() => {
    setStatus("loading");
    setScale(null);
    setNaturalWidth(0);
  }, [src]);

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
    if (!c || status !== "ok" || !bbox || scale === null) return;
    const top = bbox.y0 * scale;
    const left = bbox.x0 * scale;
    const h = (bbox.y1 - bbox.y0) * scale;
    const w = (bbox.x1 - bbox.x0) * scale;
    c.scrollTo({ top: Math.max(0, top + h / 2 - c.clientHeight / 2), left: Math.max(0, left + w / 2 - c.clientWidth / 2) });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, scale, bboxKey]);

  if (!src) return <div className="rounded-md border border-line bg-surface-2/60 p-4">{fallback}</div>;

  return (
    <div ref={containerRef} className="relative rounded-md border border-line bg-surface-2 overflow-auto" style={{ maxHeight }}>
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
