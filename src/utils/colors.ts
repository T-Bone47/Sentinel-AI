/**
 * Design tokens are stored as bare OKLCH channels (e.g. "0.62 0.185 259") so
 * Tailwind alpha modifiers work. SVG presentation attributes cannot resolve
 * `var()`, so charts must resolve tokens to concrete colors at render time.
 */
export function resolveToken(value: string, alpha?: number): string {
  if (typeof window === 'undefined') return value;
  if (!value.startsWith('var(')) return value;
  const name = value.slice(4, -1).trim();
  const raw = getComputedStyle(document.documentElement).
  getPropertyValue(name).
  trim();
  if (!raw) return value;
  if (/^(oklch|rgb|hsl|#)/.test(raw)) return raw;
  return alpha === undefined ? `oklch(${raw})` : `oklch(${raw} / ${alpha})`;
}