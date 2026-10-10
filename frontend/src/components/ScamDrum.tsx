import { useEffect, useRef, useState } from "react";

export interface DrumWord {
  text: string;
  color?: string;
}

interface Props {
  words: DrumWord[];
  /** degrees per second */
  speed: number;
  playing?: boolean;
  /** slow down + tilt with the pointer over the parent element */
  interactive?: boolean;
  fontSize: string;
  /** when set, the drum decelerates and lands one word on this value */
  settle?: DrumWord | null;
  onSettled?: () => void;
  className?: string;
}

const norm = (a: number) => ((((a + 180) % 360) + 360) % 360) - 180;
const easeOut = (p: number) => 1 - Math.pow(1 - p, 3);
const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Words on the surface of a horizontal-axis cylinder. Only transform, filter and
 * opacity change per frame; the loop pauses when off-screen or when the tab is hidden.
 */
export function ScamDrum({ words, speed, playing = true, interactive, fontSize, settle, onSettled, className = "" }: Props) {
  const root = useRef<HTMLDivElement>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const inner = useRef<HTMLDivElement>(null);
  const els = useRef<(HTMLSpanElement | null)[]>([]);
  const [override, setOverride] = useState<{ idx: number; word: DrumWord } | null>(null);
  const live = useRef({ speed, playing, onSettled });
  live.current = { speed, playing, onSettled };

  const N = words.length;
  const step = 360 / N;
  const st = useRef({
    rot: 0,
    cur: speed,
    tilt: 0,
    tiltTo: 0,
    hover: false,
    R: 400,
    settle: null as null | { from: number; to: number; t0: number },
    hold: false,
    draw: () => {},
    kick: () => {},
  });

  // draw + animation loop
  useEffect(() => {
    const s = st.current;
    const reduced = reducedMotion();
    let raf = 0;
    let last = 0;
    let visible = true;

    s.draw = () => {
      if (!inner.current || !wrap.current) return;
      inner.current.style.transform = `translateZ(${-s.R}px) rotateX(${s.rot}deg)`;
      wrap.current.style.transform = `rotateY(${s.tilt}deg)`;
      for (let i = 0; i < N; i++) {
        const el = els.current[i];
        if (!el) continue;
        const a = Math.abs(norm(i * step + s.rot));
        el.style.filter = `blur(${Math.min(14, a * 0.22).toFixed(2)}px)`;
        el.style.opacity = String(Math.max(0, Math.min(1, 1 - a / 110)));
        el.style.visibility = a > 100 ? "hidden" : "visible";
      }
    };

    const measure = () => {
      if (!root.current) return;
      s.R = 0.55 * root.current.clientHeight;
      inner.current?.style.setProperty("--R", `${s.R}px`);
      s.draw();
    };
    const ro = new ResizeObserver(measure);
    if (root.current) ro.observe(root.current);

    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (s.settle) {
        const p = Math.min(1, (now - s.settle.t0) / 700);
        s.rot = s.settle.from + (s.settle.to - s.settle.from) * easeOut(p);
        if (p >= 1) {
          s.settle = null;
          s.hold = true;
          live.current.onSettled?.();
        }
      } else if (live.current.playing && !s.hold) {
        const target = s.hover ? Math.min(4, live.current.speed) : live.current.speed;
        s.cur += (target - s.cur) * Math.min(1, dt * 4);
        s.rot += s.cur * dt;
      }
      s.tilt += (s.tiltTo - s.tilt) * Math.min(1, dt * 5);
      s.draw();
      raf = requestAnimationFrame(tick);
    };
    const start = () => {
      if (reduced || raf || !visible || document.hidden) return;
      last = performance.now();
      raf = requestAnimationFrame(tick);
    };
    const stop = () => {
      cancelAnimationFrame(raf);
      raf = 0;
    };
    s.kick = start;

    if (reduced) s.rot = -Math.floor(N / 2) * step; // static, middle word sharp
    measure();
    start();

    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting;
      visible ? start() : stop();
    });
    if (root.current) io.observe(root.current);
    const onVis = () => (document.hidden ? stop() : start());
    document.addEventListener("visibilitychange", onVis);

    // pointer interaction on the parent (the hero), so overlay text doesn't block it
    const host = root.current?.parentElement;
    const enter = () => (s.hover = true);
    const leave = () => {
      s.hover = false;
      s.tiltTo = 0;
    };
    const move = (e: PointerEvent) => {
      const r = host!.getBoundingClientRect();
      s.tiltTo = ((e.clientX - r.left) / r.width - 0.5) * 8;
    };
    if (interactive && host && !reduced) {
      host.addEventListener("pointerenter", enter);
      host.addEventListener("pointerleave", leave);
      host.addEventListener("pointermove", move);
    }
    return () => {
      stop();
      ro.disconnect();
      io.disconnect();
      document.removeEventListener("visibilitychange", onVis);
      host?.removeEventListener("pointerenter", enter);
      host?.removeEventListener("pointerleave", leave);
      host?.removeEventListener("pointermove", move);
    };
  }, [N, step, interactive]);

  // restart the loop if it had stopped
  useEffect(() => {
    st.current.kick();
  }, [playing]);

  // land on a verdict word
  useEffect(() => {
    const s = st.current;
    if (!settle) {
      setOverride(null);
      s.settle = null;
      s.hold = false;
      s.cur = live.current.speed;
      s.kick();
      return;
    }
    // next alignment at least 24deg ahead (≈ the distance a 120°/s spin covers while decelerating)
    const m = Math.floor(-(s.rot + 24) / step);
    const to = -m * step;
    const idx = ((m % N) + N) % N;
    setOverride({ idx, word: settle });
    if (reducedMotion()) {
      s.rot = to;
      s.hold = true;
      s.draw();
      const t = setTimeout(() => live.current.onSettled?.(), 50);
      return () => clearTimeout(t);
    }
    s.settle = { from: s.rot, to, t0: performance.now() };
    s.kick();
  }, [settle, N, step]);

  return (
    <div ref={root} aria-hidden="true" className={`overflow-hidden ${className}`} style={{ perspective: "900px" }}>
      <div ref={wrap} className="absolute inset-0" style={{ transformStyle: "preserve-3d" }}>
        <div ref={inner} className="absolute top-1/2 left-1/2 h-0 w-0" style={{ transformStyle: "preserve-3d" }}>
          {words.map((w, i) => {
            const shown = override?.idx === i ? override.word : w;
            return (
              <span
                key={i}
                ref={(el) => {
                  els.current[i] = el;
                }}
                className="absolute top-0 left-0 font-display leading-none whitespace-nowrap uppercase select-none"
                style={{
                  fontSize,
                  color: shown.color ?? "var(--red)",
                  transform: `translate(-50%, -50%) rotateX(${i * step}deg) translateZ(var(--R, 400px))`,
                  backfaceVisibility: "hidden",
                  willChange: "transform, filter, opacity",
                }}
              >
                {shown.text}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
