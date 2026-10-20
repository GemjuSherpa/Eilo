/** Initial design preview is a one-second cycle. Callers may tune the bounded parameter. */
export function rippleCycleMs(requested = 1000): number {
  return Number.isFinite(requested) && requested >= 500 && requested <= 4000
    ? requested
    : 1000;
}
