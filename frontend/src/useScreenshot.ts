import { useCallback, useEffect, useRef, useState } from "react";

export const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const TYPES = ["image/png", "image/jpeg", "image/webp"];

export interface ScreenshotState {
  thumb: string | null;
  reading: boolean;
  label: string;
  pct: number;
  error: string;
  /** true after a successful read, until the user edits the text */
  review: boolean;
}

const idle: ScreenshotState = { thumb: null, reading: false, label: "", pct: 0, error: "", review: false };

export function useScreenshot(onText: (text: string) => void) {
  const [s, setS] = useState<ScreenshotState>(idle);
  const abort = useRef<AbortController | null>(null);
  const thumb = useRef<string | null>(null);
  const onTextRef = useRef(onText);
  onTextRef.current = onText;

  const dropThumb = () => {
    if (thumb.current) URL.revokeObjectURL(thumb.current);
    thumb.current = null;
  };
  useEffect(() => () => { abort.current?.abort(); dropThumb(); }, []);

  const start = useCallback(async (file: File) => {
    if (!TYPES.includes(file.type)) return setS({ ...idle, error: "Please add a PNG, JPG or WebP image." });
    if (file.size > MAX_IMAGE_BYTES) return setS({ ...idle, error: "That image is over 8 MB. Please crop or compress it." });

    abort.current?.abort();
    dropThumb();
    thumb.current = URL.createObjectURL(file);
    const ctl = (abort.current = new AbortController());
    setS({ ...idle, thumb: thumb.current, reading: true, label: "Preparing screenshot reader…" });
    try {
      const { readScreenshot } = await import("./ocr.ts"); // keeps tesseract out of the main bundle
      const text = await readScreenshot(
        file,
        (p) => setS((x) => ({ ...x, pct: p.pct, label: p.phase === "prepare" ? "Preparing screenshot reader…" : `Reading screenshot… ${p.pct}%` })),
        ctl.signal,
      );
      if (!text) return setS({ ...idle, error: "We couldn't read any text in that screenshot. Try a sharper or larger one." });
      onTextRef.current(text);
      setS({ ...idle, thumb: thumb.current, review: true });
    } catch (e) {
      if ((e as Error).name === "AbortError") return; // cancel() already reset the state
      dropThumb();
      setS({ ...idle, error: "Couldn't read that screenshot. You can paste the text instead." });
    }
  }, []);

  const cancel = useCallback(() => {
    abort.current?.abort();
    dropThumb();
    setS(idle);
  }, []);

  const clearReview = useCallback(() => setS((x) => (x.review ? { ...x, review: false } : x)), []);

  return { s, start, cancel, clearReview };
}
