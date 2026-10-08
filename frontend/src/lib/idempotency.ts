/**
 * Idempotency keys: identical payloads submitted from the same form instance reuse
 * the same key (double-click / retry safe); a changed payload gets a new key.
 */
const keys = new Map<string, string>();

export function idemKey(scope: string, payload: unknown) {
  const k = `${scope}:${JSON.stringify(payload)}`;
  let v = keys.get(k);
  if (!v) {
    v = crypto.randomUUID();
    keys.set(k, v);
  }
  return v;
}

/** Forget keys for a scope after a successful mutation so the next intent is new. */
export function releaseKeys(scope: string) {
  for (const k of keys.keys()) if (k.startsWith(`${scope}:`)) keys.delete(k);
}
