// On-device screenshot reading. Loaded with a dynamic import() only when the user adds an image.
// The image never leaves the browser: only the recognised TEXT is ever sent to the backend.
import { cleanOcrText } from "./ocrClean.ts";

export type OcrProgress = { phase: "prepare" | "read"; pct: number };

const MAX_SIDE = 4000; // a huge screenshot must not exhaust memory

/** Scale 2x if narrow, grayscale, mild contrast, and flip dark-mode chats to dark-on-light. */
export async function preprocess(file: Blob): Promise<HTMLCanvasElement> {
  const bmp = await createImageBitmap(file);
  let scale = bmp.width < 1500 ? 2 : 1;
  scale = Math.min(scale, MAX_SIDE / Math.max(bmp.width, bmp.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(bmp.width * scale));
  canvas.height = Math.max(1, Math.round(bmp.height * scale));
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.drawImage(bmp, 0, 0, canvas.width, canvas.height);
  bmp.close();

  const img = ctx.getImageData(0, 0, canvas.width, canvas.height);
  const d = img.data;
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) {
    const g = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
    d[i] = d[i + 1] = d[i + 2] = g;
    sum += g;
  }
  const invert = sum / (d.length / 4) < 110;
  for (let i = 0; i < d.length; i += 4) {
    let v = Math.max(0, Math.min(255, (d[i] - 128) * 1.25 + 128));
    if (invert) v = 255 - v;
    d[i] = d[i + 1] = d[i + 2] = v;
  }
  ctx.putImageData(img, 0, 0);
  return canvas;
}

export async function readScreenshot(file: Blob, onProgress: (p: OcrProgress) => void, signal: AbortSignal): Promise<string> {
  const canvas = await preprocess(file);
  if (signal.aborted) throw new DOMException("cancelled", "AbortError");
  onProgress({ phase: "prepare", pct: 0 });

  const mod = (await import("tesseract.js")) as typeof import("tesseract.js");
  const createWorker = mod.createWorker ?? (mod as unknown as { default: typeof mod }).default.createWorker;
  const worker = await createWorker("eng", 1, {
    logger: (m: { status: string; progress: number }) => {
      if (m.status === "recognizing text") onProgress({ phase: "read", pct: Math.round(m.progress * 100) });
    },
  });
  const onAbort = () => void worker.terminate();
  signal.addEventListener("abort", onAbort);
  try {
    if (signal.aborted) throw new DOMException("cancelled", "AbortError");
    const { data } = await worker.recognize(canvas);
    if (signal.aborted) throw new DOMException("cancelled", "AbortError");
    return cleanOcrText(data.text);
  } catch (e) {
    if (signal.aborted) throw new DOMException("cancelled", "AbortError");
    throw e;
  } finally {
    signal.removeEventListener("abort", onAbort);
    await worker.terminate().catch(() => {});
  }
}
