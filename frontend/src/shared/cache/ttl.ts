/** Shared cache policy helpers. Feature caches own storage and keys. */
export function isFresh(timestamp: number, ttlMs: number, now = Date.now()): boolean {
  return Number.isFinite(timestamp) && now - timestamp >= 0 && now - timestamp < ttlMs;
}

export function pruneExpired<T extends { timestamp: number }>(
  entries: Record<string, T>,
  ttlMs: number,
  now = Date.now(),
): Record<string, T> {
  return Object.fromEntries(
    Object.entries(entries).filter(([, entry]) => isFresh(entry.timestamp, ttlMs, now)),
  );
}
