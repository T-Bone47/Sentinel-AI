import { useEffect, useRef, useState } from 'react';

/** Animates a number from 0 to `target`, respecting reduced-motion. */
export function useCountUp(target: number, duration = 900, decimals = 0): number {
  const [value, setValue] = useState(0);
  const frame = useRef<number>();

  useEffect(() => {
    const reduced =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      setValue(target);
      return;
    }
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - progress, 3);
      const next = target * eased;
      setValue(Number(next.toFixed(decimals)));
      if (progress < 1) frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
  }, [target, duration, decimals]);

  return value;
}